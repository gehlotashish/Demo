import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import VotingClassifier
import joblib
import pandas_ta as ta
import os

# --- Feature Engineering ---
def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract advanced predictive features from OHLCV/option chain DataFrame.
    Includes: EMA, RSI, MACD, Supertrend, Bollinger Bands, ATR, ADX, VWAP, Stochastic, OI, IV, PCR, etc.
    Handles NaN and outliers robustly.
    """
    features = pd.DataFrame()
    # Basic features
    features['strike'] = df.get('strike', pd.Series([0]*len(df)))
    features['CE_LTP'] = df.get('CE_LTP', pd.Series([0]*len(df)))
    features['PE_LTP'] = df.get('PE_LTP', pd.Series([0]*len(df)))
    features['CE_IV'] = df.get('CE_IV', pd.Series([0]*len(df)))
    features['PE_IV'] = df.get('PE_IV', pd.Series([0]*len(df)))
    features['CE_OI'] = df.get('CE_OI', pd.Series([0]*len(df)))
    features['PE_OI'] = df.get('PE_OI', pd.Series([0]*len(df)))
    features['CE_ChangeOI'] = df.get('CE_ChangeOI', pd.Series([0]*len(df)))
    features['PE_ChangeOI'] = df.get('PE_ChangeOI', pd.Series([0]*len(df)))
    features['CE_Volume'] = df.get('CE_Volume', pd.Series([0]*len(df)))
    features['PE_Volume'] = df.get('PE_Volume', pd.Series([0]*len(df)))
    # Put/Call Ratio
    features['PCR_OI'] = features['PE_OI'] / (features['CE_OI'] + 1e-6)
    features['PCR_Volume'] = features['PE_Volume'] / (features['CE_Volume'] + 1e-6)
    # Technical indicators (on LTP or Close)
    price = df['CE_LTP'] if 'CE_LTP' in df else df.get('Close', pd.Series([0]*len(df)))
    features['EMA_20'] = ta.ema(price, length=20)
    features['EMA_50'] = ta.ema(price, length=50)
    features['RSI'] = ta.rsi(price, length=14)
    macd = ta.macd(price)
    features['MACD'] = macd['MACD_12_26_9']
    features['MACDs'] = macd['MACDs_12_26_9']
    features['MACDh'] = macd['MACDh_12_26_9']
    # Supertrend (on OHLC)
    if all(x in df for x in ['High', 'Low', 'Close']):
        st = ta.supertrend(df['High'], df['Low'], df['Close'])
        features['Supertrend'] = st['SUPERT_7_3.0']
    # Bollinger Bands
    bb = ta.bbands(price, length=20)
    features['Boll_Upper'] = bb['BBU_20_2.0']
    features['Boll_Mid'] = bb['BBM_20_2.0']
    features['Boll_Lower'] = bb['BBL_20_2.0']
    # ATR, ADX
    if all(x in df for x in ['High', 'Low', 'Close']):
        features['ATR'] = ta.atr(df['High'], df['Low'], df['Close'])
        features['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
    # VWAP
    if all(x in df for x in ['High', 'Low', 'Close', 'Volume']):
        features['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
    # Stochastic
    if all(x in df for x in ['High', 'Low', 'Close']):
        stoch = ta.stoch(df['High'], df['Low'], df['Close'])
        features['Stoch_K'] = stoch['STOCHk_14_3_3']
        features['Stoch_D'] = stoch['STOCHd_14_3_3']
    # Fill NaN and clip outliers
    features = features.fillna(0)
    features = features.clip(lower=-1e6, upper=1e6)
    return features

# --- Model Training ---
def train_model(features: pd.DataFrame, labels: pd.Series, model_type: str = 'auto'):
    """
    Train and save an advanced ML model (XGBoost > RandomForest > DecisionTree/Logistic).
    Uses GridSearchCV for hyperparameter tuning and cross-validation.
    """
    model = None
    best_score = 0
    if model_type == 'xgb' or model_type == 'auto':
        try:
            from xgboost import XGBClassifier
            param_grid = {
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.2],
                'n_estimators': [50, 100, 200]
            }
            xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
            grid = GridSearchCV(xgb, param_grid, cv=3, n_jobs=-1)
            grid.fit(features, labels)
            model = grid.best_estimator_
            best_score = grid.best_score_
        except ImportError:
            print('XGBoost not installed, falling back to RandomForest.')
    if model is None and (model_type == 'rf' or model_type == 'auto'):
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 5, 7]
        }
        rf = RandomForestClassifier()
        grid = GridSearchCV(rf, param_grid, cv=3, n_jobs=-1)
        grid.fit(features, labels)
        model = grid.best_estimator_
        best_score = grid.best_score_
    if model is None and (model_type == 'tree' or model_type == 'auto'):
        model = DecisionTreeClassifier()
        scores = cross_val_score(model, features, labels, cv=3)
        best_score = scores.mean()
        model.fit(features, labels)
    if model is None:
        model = LogisticRegression()
        scores = cross_val_score(model, features, labels, cv=3)
        best_score = scores.mean()
        model.fit(features, labels)
    print(f"Best CV score: {best_score:.4f}")
    joblib.dump(model, 'model.pkl')
    return model

def train_ensemble_model(features: pd.DataFrame, labels: pd.Series):
    """
    Train an ensemble model (XGBoost, RandomForest, LogisticRegression) with majority voting.
    Uses GridSearchCV for each base model.
    Saves ensemble as model_ensemble.pkl.
    """
    estimators = []
    # XGBoost
    try:
        from xgboost import XGBClassifier
        param_grid = {
            'max_depth': [3, 5],
            'learning_rate': [0.01, 0.1],
            'n_estimators': [50, 100]
        }
        xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
        grid = GridSearchCV(xgb, param_grid, cv=3, n_jobs=-1)
        grid.fit(features, labels)
        estimators.append(('xgb', grid.best_estimator_))
    except ImportError:
        pass
    # RandomForest
    param_grid = {
        'n_estimators': [50, 100],
        'max_depth': [3, 5]
    }
    rf = RandomForestClassifier()
    grid = GridSearchCV(rf, param_grid, cv=3, n_jobs=-1)
    grid.fit(features, labels)
    estimators.append(('rf', grid.best_estimator_))
    # LogisticRegression
    lr = LogisticRegression(max_iter=200)
    estimators.append(('lr', lr.fit(features, labels)))
    # Voting ensemble
    ensemble = VotingClassifier(estimators=estimators, voting='soft')
    ensemble.fit(features, labels)
    joblib.dump(ensemble, 'model_ensemble.pkl')
    return ensemble

def create_dummy_labels(df: pd.DataFrame) -> pd.Series:
    """
    Create dummy labels for training (for demo: 1 if CE_LTP > PE_LTP else 0)
    """
    return (df['CE_LTP'] > df['PE_LTP']).astype(int)

if __name__ == "__main__":
    from data_fetcher import fetch_nse_option_chain
    model_type = os.getenv('MODEL_TYPE', 'auto')
    print(f"Fetching latest option chain...")
    df = fetch_nse_option_chain('BANKNIFTY')
    print("Extracting features...")
    features = extract_features(df)
    print("Creating dummy labels...")
    labels = create_dummy_labels(df)
    print(f"Training model ({model_type})...")
    train_model(features, labels, model_type=model_type)
    print("Model trained and saved as model.pkl!") 