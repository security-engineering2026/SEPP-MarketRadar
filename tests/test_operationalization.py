from marketradar.operationalization import run_local_operationalization_lab


def test_operationalization_reaches_1000_to_7_to_3_and_payment():
    result = run_local_operationalization_lab(1000)
    assert result["pass"] is True
    assert result["opportunities"] == 1000
    assert result["evidence"] == 1000
    assert result["top7"] == 7
    assert result["do_now"] == 3
    assert result["lifecycle"]["state_after_claim"] == "DELIVERED"
    assert result["lifecycle"]["final_state"] == "PAID"
    assert result["product_recommendations"] >= 1
    assert result["skill_gaps"] >= 1
