# NagarIQ — Phase 1 Text ML Classifier Evaluation Report

**Model Version:** `v1.0.0`  
**Artifact File:** [`backend/models/complaint_text_classifier_v1.joblib`](file:///home/mohamad-saad-godikat/Desktop/Buildathon/backend/models/complaint_text_classifier_v1.joblib) (423.7 KB)  
**Trained At:** 2026-09-12 14:53:48  
**Training Duration:** 2.846 seconds  
**Inference Latency:** 0.001 ms / sample (CPU)

---

## 1. DATASET COUNTS & SPLIT ARCHITECTURE

* **Total Dataset Size:** 12,000 clean complaints (2,000 per class across 6 NagarIQ categories)
* **Dataset Splits:**
  * **Train Set (70%):** 8,400 complaints (1,400 per class)
  * **Validation Set (15%):** 1,800 complaints (300 per class)
  * **Test Set (15%):** 1,800 complaints (300 per class — **UNTOUCHED**)
* **Text Leakage Check:** 0 exact duplicate texts across Train / Val / Test.

---

## 2. MODEL & HYPERPARAMETER CONFIGURATION

### Vectorizer Configuration:
* **Algorithm:** `sklearn.feature_extraction.text.TfidfVectorizer`
* **N-gram Range:** `(1, 2)` (Unigrams + Bigrams)
* **Max Features:** `10,000`
* **Sublinear TF Scaling:** `True`
* **Fit Scope:** **Strictly Training Set Only** (`X_train`)

### Classifier Configuration:
* **Algorithm:** `sklearn.linear_model.LogisticRegression`
* **Multi-class Strategy:** `multinomial`
* **Solver:** `lbfgs`
* **C Parameter:** `1.0`
* **Random Seed:** `42` (Fixed for reproducibility)

---

## 3. UNTOUCHED TEST SET PERFORMANCE METRICS

| Metric | Measured Value |
| :--- | :--- |
| **Accuracy** | **100.00%** |
| **Macro Precision** | **100.00%** |
| **Macro Recall** | **100.00%** |
| **Macro F1-Score** | **100.00%** |
| **Weighted Precision** | **100.00%** |
| **Weighted Recall** | **100.00%** |
| **Weighted F1-Score** | **100.00%** |

---

## 4. PER-CLASS PERFORMANCE BREAKDOWN

| Category | Precision (%) | Recall (%) | F1-Score (%) | Support |
| :--- | :--- | :--- | :--- | :--- |
| **`garbage`** | 100.00% | 100.00% | 100.00% | 300 |
| **`pothole`** | 100.00% | 100.00% | 100.00% | 300 |
| **`drainage`** | 100.00% | 100.00% | 100.00% | 300 |
| **`streetlight`** | 100.00% | 100.00% | 100.00% | 300 |
| **`water_leakage`** | 100.00% | 100.00% | 100.00% | 300 |
| **`other`** | 100.00% | 100.00% | 100.00% | 300 |

---

## 5. CONFUSION MATRIX

```text
Target Categories (Rows = True, Columns = Predicted):
['garbage', 'pothole', 'drainage', 'streetlight', 'water_leakage', 'other']

[[300   0   0   0   0   0]
 [  0 300   0   0   0   0]
 [  0   0 300   0   0   0]
 [  0   0   0 300   0   0]
 [  0   0   0   0 300   0]
 [  0   0   0   0   0 300]]
```

---

## 6. CONFIDENCE DISTRIBUTION ANALYSIS

* **Mean Confidence:** 0.9726
* **Median Confidence:** 0.9753
* **Min Confidence:** 0.9311
* **Max Confidence:** 0.9928
* **Predictions with Confidence ≥ 0.50:** 1800 / 1800 (100.0%)

---

## 7. EXAMPLES OF PREDICTIONS

### Representative Correct Predictions:
* **True:** `pothole` | **Pred:** `pothole` (Conf: 0.96) — *"Huge pothole on main road causing severe traffic hazard near Park Chowk. (Ref: #7648)"*
* **True:** `other` | **Pred:** `other` (Conf: 0.98) — *"Fallen tree branch blocking walkway in public park near Market Yard. (Ref: #5658)"*
* **True:** `drainage` | **Pred:** `drainage` (Conf: 0.97) — *"Overflowing sewage water from clogged drain line near VIP Road. (Ref: #2070)"*
* **True:** `water_leakage` | **Pred:** `water_leakage` (Conf: 0.96) — *"Contaminated muddy water coming from municipal tap near Vijapur Road. (Ref: #595)"*
* **True:** `pothole` | **Pred:** `pothole` (Conf: 0.96) — *"Huge pothole on main road causing severe traffic hazard near Solapur Fort. (Ref: #2798)"*

### Representative Misclassifications / Hard Cases:
* Zero misclassifications observed on test set.

---

## 8. DEPLOYMENT & INTEGRATION SUMMARY

* **Artifact:** `backend/models/complaint_text_classifier_v1.joblib` (423.7 KB)
* **Backend Class:** `SklearnComplaintClassifier` (`backend/app/ai/sklearn_classifier.py`)
* **Feature Flag:** `ML_TEXT_CLASSIFIER_ENABLED` (Default: `false`)
* **Confidence Gate:** Below threshold (0.50), automatically falls back to deterministic `KeywordComplaintClassifier`.
