from datasets import load_dataset
import pandas as pd

ds = load_dataset("deepset/prompt-injections")
df = pd.concat([ds["train"].to_pandas(), ds["test"].to_pandas()])
df["label"] = df["label"].map({0: "BENIGN", 1: "PROMPT_INJECTION"})
df[["text", "label"]].to_csv("injection_dataset.csv", index=False)