from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd


DATA_URL = (
    "https://raw.githubusercontent.com/alexeygrigorev/"
    "mlbookcamp-code/master/chapter-02-car-price/data.csv"
)
DATA_FILE = Path("data.csv")
SEED = 2


def download_data() -> None:
    if not DATA_FILE.exists():
        print("Downloading data.csv ...")
        urlretrieve(DATA_URL, DATA_FILE)


def prepare_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    df.columns = df.columns.str.lower().str.replace(" ", "_")

    string_columns = list(df.dtypes[df.dtypes == "object"].index)
    for col in string_columns:
        df[col] = df[col].str.lower().str.replace(" ", "_")

    return df


def split_data(df: pd.DataFrame):
    n = len(df)
    n_val = int(n * 0.2)
    n_test = int(n * 0.2)
    n_train = n - n_val - n_test

    idx = np.arange(n)
    np.random.seed(SEED)
    np.random.shuffle(idx)

    df_train = df.iloc[idx[:n_train]].reset_index(drop=True)
    df_val = df.iloc[idx[n_train : n_train + n_val]].reset_index(drop=True)
    df_test = df.iloc[idx[n_train + n_val :]].reset_index(drop=True)

    y_train = np.log1p(df_train.msrp.values)
    y_val = np.log1p(df_val.msrp.values)
    y_test = np.log1p(df_test.msrp.values)

    del df_train["msrp"]
    del df_val["msrp"]
    del df_test["msrp"]

    return df_train, df_val, df_test, y_train, y_val, y_test


def make_features(df: pd.DataFrame) -> np.ndarray:
    features = [
        "engine_hp",
        "engine_cylinders",
        "highway_mpg",
        "city_mpg",
        "popularity",
    ]
    return df[features].fillna(0).values


def train_linear_regression(X: np.ndarray, y: np.ndarray):
    ones = np.ones(X.shape[0])
    X = np.column_stack([ones, X])

    gram = X.T @ X
    weights = np.linalg.solve(gram, X.T @ y)

    return weights[0], weights[1:]


def predict(X: np.ndarray, bias: float, weights: np.ndarray) -> np.ndarray:
    return bias + X @ weights


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    error = y_true - y_pred
    return np.sqrt((error**2).mean())


def main() -> None:
    download_data()
    df = prepare_data()
    df_train, df_val, df_test, y_train, y_val, y_test = split_data(df)

    X_train = make_features(df_train)
    X_val = make_features(df_val)
    X_test = make_features(df_test)

    bias, weights = train_linear_regression(X_train, y_train)
    y_val_pred = predict(X_val, bias, weights)
    y_test_pred = predict(X_test, bias, weights)

    print(f"Rows: train={len(df_train)}, val={len(df_val)}, test={len(df_test)}")
    print(f"Validation RMSE: {rmse(y_val, y_val_pred):.3f}")
    print(f"Test RMSE: {rmse(y_test, y_test_pred):.3f}")

    predicted_price = np.expm1(y_test_pred[0])
    actual_price = np.expm1(y_test[0])
    print(f"Example predicted price: ${predicted_price:,.0f}")
    print(f"Example actual price:    ${actual_price:,.0f}")


if __name__ == "__main__":
    main()

