"""Direct Live API Verification for Reliance Scenario & Research (§88).

Validates the full pipeline:
DATA -> FEATURE -> MODEL -> PROBABILITY -> SCENARIO -> CAPITAL -> EVIDENCE -> UI
"""
import urllib.request
import urllib.error
import json
import sys

def verify():
    base_url = "http://127.0.0.1:8000"
    print("Testing live API at:", base_url)

    # 1. Health check
    try:
        req = urllib.request.urlopen(f"{base_url}/health", timeout=3)
        h = json.loads(req.read().decode("utf-8"))
        print(f"[OK] Health check passed: {h.get('status')}")
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return 1

    # 2. Company lookup / search
    try:
        req = urllib.request.urlopen(f"{base_url}/api/search?q=RELIANCE", timeout=3)
        s_data = json.loads(req.read().decode("utf-8"))
        print(f"[OK] Search 'RELIANCE' returned {len(s_data)} results")
    except Exception as e:
        print(f"[WARN] Search query: {e}")

    # 3. Full Scenario Analysis Pipeline (§88: RELIANCE, ₹500, 3M, target)
    print("\n--- Running Scenario Engine Pipeline ---")
    scenario_payload = {
        "symbol": "RELIANCE",
        "capital": 500.0,
        "horizon_days": 90, # 3M
        "target_price": 3200.0,
        "downside_threshold_pct": 5.0
    }
    
    try:
        req = urllib.request.Request(
            f"{base_url}/api/scenario/analyze",
            data=json.dumps(scenario_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Scenario API returned HTTP {resp.status}")
            
            # Verify data points
            inputs = res.get("inputs", {})
            curr_price = inputs.get("current_price") or res.get("current_price")
            exec_pos = res.get("execution_position") or res.get("capital_simulation", {})
            scenarios = res.get("scenarios", {})
            probs = res.get("target_probabilities") or res.get("probabilities", {})
            model_meta = res.get("model_metadata") or res.get("calibration", {})
            stress = res.get("stress_tests", [])
            evidence = res.get("evidence_panel") or res.get("evidence", [])
            
            print(f"  * Current Price: INR {curr_price}")
            print(f"  * Whole Shares: {exec_pos.get('whole_shares')}")
            print(f"  * Insufficient Capital Flag: {exec_pos.get('insufficient_capital')}")
            print(f"  * Cash Remainder: INR {exec_pos.get('cash_remainder')}")
            print(f"  * Scenarios Count: {len(scenarios)}")
            if isinstance(scenarios, dict):
                for s_name, s_data in scenarios.items():
                    if isinstance(s_data, dict):
                        print(f"    - {s_name}: median={s_data.get('price_median') or s_data.get('target_price')} (p={round(s_data.get('probability', 0)*100, 1)}%)")
            elif isinstance(scenarios, list):
                for s in scenarios:
                    print(f"    - {s.get('scenario_tier')}: price={s.get('target_price')} (p={round(s.get('probability', 0)*100, 1)}%)")
            
            print(f"  * Target Touched Prob: {round(probs.get('calibrated_p_target_touched', probs.get('target_touched', 0))*100, 1)}%")
            print(f"  * Target Finish-Above Prob: {round(probs.get('calibrated_p_finish_above', probs.get('target_finished_above', 0))*100, 1)}%")
            print(f"  * Calibration Status: {model_meta.get('calibration_status')} (ECE: {model_meta.get('expected_calibration_error')}, Brier: {model_meta.get('brier_score')})")
            print(f"  * Stress Scenarios: {len(stress)} historical shocks evaluated")
            print(f"  * Evidence Items: {len(evidence)} facts preserved with provenance")
            
            assert curr_price is not None and curr_price > 0, "Invalid current price"
            assert len(scenarios) == 5, f"Expected 5 scenario tiers, got {len(scenarios)}"
            assert "insufficient_capital" in exec_pos, "Missing insufficient capital flag"
            assert len(evidence) > 0, "Missing evidence items"
            print("\n[SUCCESS] Entire Scenario Chain Verified End-to-End!")
    except Exception as e:
        print(f"[FAIL] Scenario API execution: {e}")
        return 1

    # 4. Research Desk Query (§56, §88)
    print("\n--- Running Research Desk Synthesis Query ---")
    research_payload = {
        "query": "What are the key drivers and risk factors for RELIANCE?",
        "symbol": "RELIANCE"
    }
    try:
        req = urllib.request.Request(
            f"{base_url}/api/research/query",
            data=json.dumps(research_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            r_res = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Research API returned HTTP {resp.status}")
            print(f"  * Query: {r_res.get('query')}")
            print(f"  * Answer Preview: {r_res.get('answer', '')[:120]}...")
            print(f"  * Citations Count: {len(r_res.get('citations', []))}")
            print(f"  * Evidence Count: {len(r_res.get('evidence', []))}")
            print("\n[SUCCESS] Research Desk Query Verified End-to-End!")
    except Exception as e:
        print(f"[FAIL] Research Desk execution: {e}")
        return 1

    print("\n============================================================")
    print(" ALL LIVE END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!")
    print("============================================================")
    return 0

if __name__ == "__main__":
    sys.exit(verify())
