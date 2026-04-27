import json
import os
import urllib.error
import urllib.request
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .serializers import ChapaInitPaymentSerializer, PaymentSerializer
from transactions.services import finalize_return_for_borrow

def _norm_role(role):
    return "".join(str(role or "").upper().split())


def _append_query_param(url, key, value):
    if not url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{key}={value}"


def _chapa_request(method, path, payload=None):
    base_url = getattr(settings, "CHAPA_BASE_URL", "https://api.chapa.co").rstrip("/")
    secret_key = getattr(settings, "CHAPA_SECRET_KEY", os.getenv("CHAPA_SECRET_KEY", ""))
    
    if not secret_key:
        return {"status": "error", "message": "Server configuration error: Missing Secret Key"}

    url = f"{base_url}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None

    request = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"message": body or str(exc)}
        return {"status": "error", "message": parsed.get("message", "API Error"), "data": parsed}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

class ChapaInitializePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChapaInitPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return_obj = serializer.validated_data["return_obj"]
        member_user = return_obj.borrow.member
        member_profile = serializer.validated_data["member_profile"]
        amount = serializer.validated_data["amount"]

        if _norm_role(getattr(request.user, "role", None)) == "MEMBER" and request.user != member_user:
            return Response({"detail": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            payment = Payment.objects.filter(return_id=return_obj, status="PENDING").first()
            if not payment:
                tx_ref = f"RTN-{uuid.uuid4().hex[:12].upper()}"
                payment = Payment.objects.create(
                    member_id=member_profile,
                    return_id=return_obj,
                    fine_amount=amount,
                    method="TRANSFER",
                    transaction_reference=tx_ref,
                    status="PENDING",
                )
            else:
                tx_ref = payment.transaction_reference

        payload = {
            "amount": str(amount),
            "currency": getattr(settings, "CHAPA_CURRENCY", "ETB"),
            "email": member_user.email,
            "first_name": member_user.first_name or "Member",
            "last_name": member_user.last_name or "User",
            "tx_ref": tx_ref,
            "callback_url": serializer.validated_data.get("callback_url", getattr(settings, "CHAPA_CALLBACK_URL", "")),
            "return_url": _append_query_param(
                serializer.validated_data.get("return_url", getattr(settings, "CHAPA_RETURN_URL", "")),
                "tx_ref",
                tx_ref,
            ),
            "customization": {
                "title": "Library Fine Payment",
                "description": f"Fine for return {return_obj.id}",
            }
        }

        chapa_response = _chapa_request("POST", "/v1/transaction/initialize", payload=payload)

        if chapa_response.get("status") != "success":
            return Response({
                "detail": "Chapa initialization failed.",
                "chapa_response": chapa_response
            }, status=status.HTTP_400_BAD_REQUEST)

        checkout_url = chapa_response.get("data", {}).get("checkout_url")
        return Response({
            "payment": PaymentSerializer(payment).data,
            "checkout_url": checkout_url
        }, status=status.HTTP_201_CREATED)

class ChapaVerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, tx_ref):
        payment = Payment.objects.select_related("return_id__borrow__member").filter(
            transaction_reference=tx_ref
        ).first()

        if not payment:
            return Response({"detail": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

        if _norm_role(getattr(request.user, "role", None)) == "MEMBER":
            if request.user != payment.return_id.borrow.member:
                return Response({"detail": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        chapa_response = _chapa_request("GET", f"/v1/transaction/verify/{tx_ref}")
        data = chapa_response.get("data", {})
        
        remote_status = str(data.get("status", "")).lower()
        success_states = {"success", "successful", "completed", "paid"}
        
        if chapa_response.get("status") == "success" and remote_status in success_states:
            try:
                paid_amount = Decimal(str(data.get("amount")))
                expected_currency = getattr(settings, "CHAPA_CURRENCY", "ETB")
                remote_currency = data.get("currency", expected_currency)

                if paid_amount >= payment.fine_amount and remote_currency == expected_currency:
                    payment.status = "COMPLETED"
                else:
                    payment.status = "FAILED"
            except (InvalidOperation, TypeError):
                payment.status = "FAILED"
        else:
            payment.status = "FAILED"

        payment.save(update_fields=["status"])

        if payment.status == "COMPLETED":
            finalize_return_for_borrow(payment.return_id.borrow)

        return Response({
            "payment": PaymentSerializer(payment).data,
            "chapa_status": remote_status
        }, status=status.HTTP_200_OK)
