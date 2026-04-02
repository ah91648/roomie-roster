# ML Grocery Prediction System - Phase 1: Baseline Predictor

**Status:** ✅ Complete
**Model Version:** `sma_v1`
**Target Accuracy:** 70-75% precision@7days
**Implementation Date:** 2025-11-12

---

## Overview

Phase 1 implements a **Simple Moving Average (SMA) baseline predictor** that forecasts when grocery items will run out. This establishes a performance benchmark for future advanced ML models (Phase 2: Prophet + Survival Analysis).

**Key Achievement:** Production-ready prediction infrastructure with daily automated predictions, accuracy tracking, and API endpoints for frontend integration.

---

## Algorithm: Simple Moving Average (SMA)

### Core Concept

For each item, the predictor:
1. Retrieves purchase history (by item name + category)
2. Calculates intervals between consecutive purchases
3. Applies **Exponential Moving Average** (EMA) to weight recent purchases more heavily
4. Predicts next depletion date: `last_purchase_date + avg_interval`
5. Assigns confidence score based on data quality (purchase count + variance)

### Mathematical Details

**Exponential Moving Average:**
```python
EMA(t) = α × value(t) + (1 - α) × EMA(t-1)
where α = 0.3 (smoothing factor)
```

**Confidence Scoring:**
```python
confidence = min(1.0, (purchase_count / 5.0) × 0.7 + consistency_bonus)

where consistency_bonus:
  - 0.2 if CV < 0.2  (very consistent)
  - 0.1 if CV < 0.4  (moderately consistent)
  - 0.0 otherwise     (high variance)

CV = coefficient of variation = std_dev / mean
```

### Fallback Strategy

| Purchase Count | Strategy | Confidence Cap |
|----------------|----------|----------------|
| 3+ purchases | Per-item SMA | Up to 1.0 |
| 1-2 purchases | Category-level average | Max 0.4 |
| 0 purchases | No prediction | N/A |

---

## Implementation Architecture

### 1. Database Schema

**Migration:** `backend/migrations/versions/20251112_add_prediction_fields.py`

**New Fields (ShoppingItem model):**
```python
predicted_depletion_date = db.Column(db.DateTime, nullable=True)
prediction_confidence = db.Column(db.Float, nullable=True)  # 0-1 range
prediction_model_version = db.Column(db.String(50), server_default='sma_v1')
```

**Indexes:**
- `idx_shopping_predicted_depletion` on `predicted_depletion_date` (partial, non-NULL only)

**Constraints:**
- `ck_shopping_confidence_range`: Ensures `prediction_confidence` is between 0 and 1

---

### 2. Prediction Service

**File:** `backend/utils/grocery_prediction_service.py`

**Class:** `GroceryPredictionService`

**Key Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `calculate_sma(item_id, window)` | Calculate SMA prediction for single item | Prediction dict or None |
| `calculate_category_fallback(category, last_purchase_date)` | Category-level average fallback | Prediction dict or None |
| `generate_all_predictions(min_purchases)` | Batch predict all eligible items | Stats dict |
| `evaluate_accuracy()` | Calculate precision@7days, MAE, coverage | Metrics dict |
| `get_confidence_score(item_id)` | Get confidence for specific item | Float (0-1) |

**Configuration:**
```python
MODEL_VERSION = "sma_v1"
MIN_PURCHASES_FOR_PREDICTION = 2
DEFAULT_WINDOW_SIZE = 5
EMA_ALPHA = 0.3  # Higher = more weight on recent purchases
```

---

### 3. Database Handler Methods

**File:** `backend/utils/database_data_handler.py`

**New Methods:**

| Method | Purpose | Database Mode | JSON Mode |
|--------|---------|---------------|-----------|
| `get_shopping_item_by_id(item_id)` | Fetch single item by ID | SQLAlchemy query | List filter |
| `get_shopping_items(status, category)` | Fetch items with filters | SQLAlchemy query + filters | List comprehension |
| `get_item_purchase_intervals_by_id(item_id)` | Get intervals for specific item | Date arithmetic on matched items | Delegates to name-based method |
| `update_shopping_item(item_id, data)` | Update item (including predictions) | SQLAlchemy update + commit | List update + file write |

---

### 4. Scheduled Jobs

**File:** `backend/utils/scheduler_service.py`

**New Job:**
```python
# Schedule daily grocery prediction generation (runs daily at 3 AM)
scheduler.add_job(
    func=_generate_daily_predictions,
    trigger='cron',
    hour=3, minute=0,
    id='daily_prediction_generation',
    name='Generate Grocery Depletion Predictions',
    replace_existing=True,
    misfire_grace_time=1800  # 30 min grace period
)
```

**Job Behavior:**
- Runs automatically at 3 AM daily
- Calls `prediction_service.generate_all_predictions(min_purchases=2)`
- Logs stats: predictions generated, category fallbacks, insufficient data count

---

### 5. API Endpoints

**File:** `backend/app.py`

#### GET `/api/ml/predictions`
**Auth:** Required
**Rate Limit:** 50 requests/min
**Returns:** All active predictions sorted by urgency (soonest first)

**Response:**
```json
{
  "predictions": [
    {
      "item_id": 42,
      "item_name": "Milk",
      "category": "Dairy",
      "predicted_depletion_date": "2025-11-19T10:30:00Z",
      "prediction_confidence": 0.85,
      "model_version": "sma_v1",
      "days_until_depletion": 7,
      "urgency": "medium"
    }
  ],
  "total_predictions": 15,
  "timestamp": "2025-11-12T14:30:00Z"
}
```

**Urgency Levels:**
- `high`: ≤ 3 days until depletion
- `medium`: 4-7 days until depletion
- `low`: > 7 days

---

#### GET `/api/ml/predictions/item/:id`
**Auth:** Required
**Rate Limit:** 50 requests/min
**Returns:** Prediction for specific item

**Response (with prediction):**
```json
{
  "item_id": 42,
  "item_name": "Milk",
  "category": "Dairy",
  "predicted_depletion_date": "2025-11-19T10:30:00Z",
  "prediction_confidence": 0.85,
  "model_version": "sma_v1",
  "days_until_depletion": 7,
  "urgency": "medium",
  "has_prediction": true
}
```

**Response (no prediction):**
```json
{
  "item_id": 42,
  "item_name": "Milk",
  "has_prediction": false,
  "message": "No prediction available (insufficient data)"
}
```

---

#### GET `/api/ml/predictions/metrics`
**Auth:** Required
**Rate Limit:** 50 requests/min
**Returns:** Model performance metrics

**Response:**
```json
{
  "metrics": {
    "precision_at_7_days": 0.73,
    "recall_at_7_days": 0.68,
    "mae": 3.2,
    "coverage": 0.45,
    "total_predictions": 28,
    "total_actual_depletions": 15,
    "evaluated_pairs": 12
  },
  "model_version": "sma_v1",
  "timestamp": "2025-11-12T14:30:00Z"
}
```

**Metrics Explained:**
- **precision_at_7_days**: Of items predicted to deplete in 7 days, what % actually did?
- **recall_at_7_days**: Of items that depleted in 7 days, what % did we predict?
- **mae**: Mean Absolute Error in days (lower is better)
- **coverage**: % of items with predictions (target: 40%+)

---

#### POST `/api/ml/predictions/refresh`
**Auth:** Required
**CSRF:** Protected
**Rate Limit:** 10 requests/min (strict)
**Returns:** Prediction generation stats

**Request:**
```bash
POST /api/ml/predictions/refresh
Headers:
  Authorization: Bearer <token>
  X-CSRF-Token: <csrf_token>
```

**Response:**
```json
{
  "message": "Predictions refreshed successfully",
  "stats": {
    "predictions_generated": 28,
    "items_processed": 50,
    "category_fallbacks": 12,
    "insufficient_data": 10
  },
  "timestamp": "2025-11-12T14:35:00Z"
}
```

---

## Evaluation Metrics

### Target Performance (Phase 1)

| Metric | Target | Current |
|--------|--------|---------|
| Precision@7days | ≥ 70% | TBD (needs 60+ days data) |
| Recall@7days | ≥ 65% | TBD |
| MAE | ≤ 4 days | TBD |
| Coverage | ≥ 40% | TBD |

### Success Criteria

✅ **Functional Requirements:**
- Predictions generated daily for items with 2+ purchases
- Confidence scores computed based on data quality
- Category fallback for items with 1 purchase
- API endpoints returning predictions with metadata

✅ **Technical Requirements:**
- Works in both PostgreSQL and JSON modes
- Scheduled job runs without errors
- Logging of prediction generation and accuracy

⏸️ **Pending (requires 60+ days production data):**
- Precision@7days ≥ 70%
- Coverage ≥ 40%
- Test coverage ≥ 80%

---

## Usage

### Programmatic Access

```python
from utils.grocery_prediction_service import GroceryPredictionService

# Initialize service
prediction_service = GroceryPredictionService(
    data_handler=data_handler,
    logger=logger
)

# Generate predictions for all items
stats = prediction_service.generate_all_predictions(min_purchases=2)
print(f"Generated {stats['predictions_generated']} predictions")

# Get prediction for specific item
prediction = prediction_service.calculate_sma(item_id=42)
if prediction:
    print(f"Predicted depletion: {prediction['predicted_depletion_date']}")
    print(f"Confidence: {prediction['confidence']:.2f}")

# Evaluate accuracy
metrics = prediction_service.evaluate_accuracy()
print(f"Precision@7days: {metrics['precision_at_7_days']:.1%}")
```

---

## Data Requirements

### Minimum Data Threshold

| Scenario | Requirement | Prediction Strategy |
|----------|-------------|---------------------|
| Item-level prediction | 2+ purchases of same item | Per-item SMA |
| Category fallback | 5+ category purchases total | Category-average SMA |
| Overall model training | 60+ days of data, 100+ depletion events | Backtest validation |

### Data Quality Metrics

**Target Metrics:**
- **Quantity field completion:** 90%+ (users enter amount + unit)
- **Depletion tracking rate:** 80%+ (users mark items as depleted)
- **Purchase history length:** 3+ purchases per frequently-bought item

---

## Deployment

### Running Migrations

```bash
cd backend
python scripts/run_migrations.py
```

### Verifying Installation

```bash
# Check migration status
python scripts/check_pending_migrations.py

# Verify prediction service loads
python -c "from utils.grocery_prediction_service import GroceryPredictionService; print('✅ Service loaded')"

# Check scheduler job
curl http://localhost:5000/api/scheduler/status
# Look for job: "Generate Grocery Depletion Predictions"
```

### Manual Prediction Trigger

```bash
# Via API
curl -X POST http://localhost:5000/api/ml/predictions/refresh \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf_token>"

# Or programmatically
python -c "
from app import prediction_service
stats = prediction_service.generate_all_predictions()
print(stats)
"
```

---

## Troubleshooting

### No Predictions Generated

**Symptom:** `total_predictions: 0` in `/api/ml/predictions`

**Causes:**
1. **Insufficient data:** Items need 2+ purchases with depletion dates
2. **Scheduler not running:** Check `/api/scheduler/status`
3. **Migration not applied:** Run `python scripts/check_pending_migrations.py`

**Solution:**
```bash
# Check data availability
curl http://localhost:5000/api/ml/depletion-history?days=90

# Manually trigger predictions
curl -X POST http://localhost:5000/api/ml/predictions/refresh \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf_token>"
```

---

### Low Precision

**Symptom:** `precision_at_7_days < 0.70`

**Causes:**
1. **High variance in purchase patterns:** Users buy irregularly
2. **Insufficient history:** Items have only 2-3 purchases
3. **Incorrect data:** Users not marking depletion dates accurately

**Solution:**
- Educate users on importance of tracking depletion dates
- Consider increasing `MIN_PURCHASES_FOR_PREDICTION` to 3
- Wait for more data (Phase 1 requires 60+ days)

---

### Scheduler Job Not Running

**Symptom:** Predictions never update automatically

**Solution:**
```bash
# Check scheduler status
curl http://localhost:5000/api/scheduler/status

# Look for job in logs
grep "daily_prediction_generation" logs/*.log

# Verify prediction service initialized
grep "GroceryPredictionService" logs/*.log
```

---

## Future Enhancements (Phase 2)

### Advanced Models (Months 3-4)

1. **Prophet for Time Series:**
   - Handles seasonality (holiday shopping patterns)
   - Detects trends (consumption rate changes)
   - Target: 85-90% precision@7days

2. **Survival Analysis (Cox Proportional Hazards):**
   - Models time-to-depletion as survival problem
   - Incorporates covariates (household size, brand, day of week)
   - Better handles censored data (items not yet depleted)

3. **Ensemble Model:**
   - Combine SMA + Prophet + Survival Analysis
   - Weighted voting based on historical accuracy
   - Adaptive weighting per item category

### Feature Engineering

**Additional Features:**
- Day of week purchased (weekend vs weekday)
- Month/season (holiday patterns)
- Household size (dynamic consumption)
- Brand (consumption rate varies by brand)
- Weather data (milk consumption increases in summer)

---

## References

- **Algorithm:** Simple Moving Average (SMA) with exponential weighting
- **Evaluation:** Precision at K, Mean Absolute Error (MAE)
- **Baseline Research:** Rolling mean benchmarks in inventory forecasting
- **Future Models:** Prophet (Facebook), Cox Proportional Hazards

---

## Changelog

### 2025-11-12 - Phase 1 Complete
- ✅ Database migration for prediction fields
- ✅ GroceryPredictionService with SMA algorithm
- ✅ DatabaseDataHandler integration (4 new methods)
- ✅ Daily scheduler job at 3 AM
- ✅ 4 API endpoints for predictions
- ⏸️ Unit tests (pending)
- ⏸️ E2E tests (pending)
- ✅ Documentation

---

**Next Phase:** Phase 2 - Advanced ML Models (Prophet + Survival Analysis)
**Trigger:** 60+ days of production data + 100+ depletion events collected
