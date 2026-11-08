# Benchmark Evaluation Report: `ios-privacy-security-audit`

## Summary
- **Suite**: `ios-privacy-security-audit` Evaluation Benchmark
- **Pass Rate**: 100.0% (4/4 scenarios passed)
- **Rules Detected**: 10/10 (100.0%)
- **Total Execution Duration**: ~3.12ms

## Scenario Results

| Scenario File | Target Area | Expected Rules | Detected | Duration | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `eval1_privacy_manifest.swift` | Apple Required Reason APIs | `PRIV_REQ_USERDEFAULTS`, `PRIV_REQ_BOOTTIME`, `PRIV_REQ_DISKSPACE`, `PRIV_REQ_FILETIME` | 4/4 | 1.23ms | ✅ Passed |
| `eval2_insecure_storage.swift` | Insecure UserDefaults Storage | `INSECURE_USERDEFAULTS_STORAGE` | 1/1 | 0.56ms | ✅ Passed |
| `eval3_hardcoded_secrets.swift` | Hardcoded API Keys & Tokens | `SEC_OPENAI_KEY`, `SEC_GOOGLE_KEY`, `SEC_AWS_KEY` | 3/3 | 0.44ms | ✅ Passed |
| `eval4_ats_biometrics.swift` | ATS Insecure HTTP & Biometric Guards | `INSECURE_HTTP_TRANSPORT`, `BIOMETRIC_CHECK_WITHOUT_CAN_EVALUATE` | 2/2 | 0.60ms | ✅ Passed |
