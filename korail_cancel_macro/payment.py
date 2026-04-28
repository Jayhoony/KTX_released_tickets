from __future__ import annotations

import json
from typing import Any

from korail2 import KorailError

from .credential_storage import PaymentCredentials


KORAIL_MOBILE = "https://smart.letskorail.com:443/classes/com.korail.mobile"
KORAIL_RESERVATION_LIST = f"{KORAIL_MOBILE}.certification.ReservationList"
KORAIL_RESERVATION_PAYMENT = f"{KORAIL_MOBILE}.payment.ReservationPayment"


class KorailPaymentError(RuntimeError):
    pass


def _korail_attr(korail: Any, name: str) -> str:
    return str(getattr(korail, name))


def get_reservation_wct_no(korail: Any, reservation: Any) -> str:
    data = {
        "Device": _korail_attr(korail, "_device"),
        "Version": _korail_attr(korail, "_version"),
        "Key": _korail_attr(korail, "_key"),
        "hidPnrNo": reservation.rsv_id,
    }
    response = korail._session.get(KORAIL_RESERVATION_LIST, params=data)
    payload = json.loads(response.text)

    if not korail._result_check(payload):
        raise KorailPaymentError("예약 상세정보 조회에 실패했습니다.")

    wct_no = payload.get("h_wct_no")
    if not wct_no:
        raise KorailPaymentError("결제에 필요한 창구번호(h_wct_no)를 찾지 못했습니다.")
    return str(wct_no)


def pay_reservation_with_card(korail: Any, reservation: Any, payment: PaymentCredentials) -> bool:
    if getattr(reservation, "buy_limit_date", "") == "00000000":
        raise KorailPaymentError("예약대기 상태는 자동결제할 수 없습니다.")

    card_type = "S" if payment.is_corporate else "J"
    wct_no = get_reservation_wct_no(korail, reservation)
    data = {
        "Device": _korail_attr(korail, "_device"),
        "Version": _korail_attr(korail, "_version"),
        "Key": _korail_attr(korail, "_key"),
        "hidPnrNo": reservation.rsv_id,
        "hidWctNo": wct_no,
        "hidTmpJobSqno1": "000000",
        "hidTmpJobSqno2": "000000",
        "hidRsvChgNo": "000",
        "hidInrecmnsGridcnt": "1",
        "hidStlMnsSqno1": "1",
        "hidStlMnsCd1": "02",
        "hidMnsStlAmt1": str(reservation.price),
        "hidCrdInpWayCd1": "@",
        "hidStlCrCrdNo1": payment.card_number,
        "hidVanPwd1": payment.card_password,
        "hidCrdVlidTrm1": payment.expire,
        "hidIsmtMnthNum1": "0",
        "hidAthnDvCd1": card_type,
        "hidAthnVal1": payment.validation_number,
        "hiduserYn": "Y",
    }

    response = korail._session.post(KORAIL_RESERVATION_PAYMENT, data=data)
    payload = json.loads(response.text)
    try:
        return bool(korail._result_check(payload))
    except KorailError as exc:
        raise KorailPaymentError(str(exc)) from exc
