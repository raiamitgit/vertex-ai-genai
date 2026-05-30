# Copyright 2026 Google LLC
# Rigorous unit tests for the surgical CSP sanitization helpers

import re
import json
from agent_executor import enforce_csp_tag, sanitize_ui_item

def test_enforce_csp_tag():
    print("----------------------------------------------------")
    print("Testing enforce_csp_tag()...")
    print("----------------------------------------------------")
    
    # Case 1: Meta tag with double quotes & single quotes (compliant)
    html_1 = '<!DOCTYPE html><html><head><meta http-equiv="Content-Security-Policy" content="connect-src \'none\';"></head><body>Test</body></html>'
    res_1 = enforce_csp_tag(html_1)
    assert 'content="connect-src \'none\';"' in res_1, "Failed Case 1"
    print("✅ Case 1 Passed: Compliant tag untouched/normalized correctly")

    # Case 2: Meta tag with single quotes & &quot; (hallucinated format)
    html_2 = '<!DOCTYPE html><html><head><meta http-equiv=\'Content-Security-Policy\' content=\'connect-src &quot;none&quot;\'></head><body>Test</body></html>'
    res_2 = enforce_csp_tag(html_2)
    assert 'content="connect-src \'none\';"' in res_2, f"Failed Case 2: {res_2}"
    print("✅ Case 2 Passed: Hallucinated single quotes and entities correctly normalized")

    # Case 3: Meta tag completely missing, head exists
    html_3 = '<!DOCTYPE html><html><head><title>Test Title</title></head><body>Test</body></html>'
    res_3 = enforce_csp_tag(html_3)
    assert 'content="connect-src \'none\';"' in res_3, "Failed Case 3"
    print("✅ Case 3 Passed: CSP meta tag injected inside head correctly")

    # Case 4: Meta tag completely missing, html exists but no head
    html_4 = '<!DOCTYPE html><html><body>Test</body></html>'
    res_4 = enforce_csp_tag(html_4)
    assert 'content="connect-src \'none\';"' in res_4, "Failed Case 4"
    assert '<head>' in res_4, "Failed Case 4: Head not synthesized"
    print("✅ Case 4 Passed: CSP meta tag injected inside synthesized head correctly")

def test_sanitize_ui_item():
    print("\n----------------------------------------------------")
    print("Testing sanitize_ui_item()...")
    print("----------------------------------------------------")
    
    # Setup hallucinated A2UI JSON dictionary item
    ui_item = {
        "surfaceUpdate": {
            "surfaceId": "userProfileSurface",
            "components": [
                {
                    "id": "linkedinButtonFrame",
                    "component": {
                        "WebFrameSrcdoc": {
                            "htmlContent": {
                                "literalString": "<!DOCTYPE html><html><head><meta http-equiv='Content-Security-Policy' content='connect-src &quot;none&quot;;'></head><body>Test</body></html>"
                            },
                            "height": 52
                        }
                    }
                }
            ]
        }
    }
    
    sanitized = sanitize_ui_item(ui_item)
    
    # Extract the resulting html Content
    comp = sanitized["surfaceUpdate"]["components"][0]
    html_content = comp["component"]["WebFrameSrcdoc"]["htmlContent"]["literalString"]
    
    print(f"Sanitized HTML output:\n{html_content}")
    
    # Validate using the EXACT original legacy regex validator from UcsA2ui (cl/900405674)
    REQUIRED_CSP_PATTERN = re.compile(
        '<meta\\s+' +
            '(?=[^>]*http-equiv\\s*=\\s*["\']Content-Security-Policy["\'])' +
            '(?=[^>]*content\\s*=\\s*["\'][^">]*connect-src\\s+\'none\'[^">]*["\'])' +
            '[^>]*/?>',
        re.IGNORECASE
    )
    
    is_matched = bool(REQUIRED_CSP_PATTERN.search(html_content))
    assert is_matched, "Sanitized HTML failed to pass the strict A2UI regex validation!"
    print("✅ UI Item Sanitizer Passed: Reconstructed HTML is 100% legacy regex compliant!")

if __name__ == "__main__":
    test_enforce_csp_tag()
    test_sanitize_ui_item()
    print("\n====================================================")
    print("🎉 ALL CSP SANITIZER UNIT TESTS PASSED FLALWESSLY!")
    print("====================================================")
