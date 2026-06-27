from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

root=Path(__file__).resolve().parents[1]
inp=root/"data"/"Portfolio_Positions.csv"
out=root/"output"/"OpenPositions_Midpoint.xlsx"

df=pd.read_csv(inp)
lookup={c.lower().strip():c for c in df.columns}
def find(term):
    for k,v in lookup.items():
        if term in k:
            return v
    return None
bid=find("bid"); ask=find("ask"); qty=find("quantity") or find("qty")
df["Mid"]=(pd.to_numeric(df[bid],errors="coerce")+pd.to_numeric(df[ask],errors="coerce"))/2
q=pd.to_numeric(df[qty],errors="coerce").fillna(1) if qty else 1
df["Mid Value"]=df["Mid"]*100*q
with pd.ExcelWriter(out,engine="openpyxl") as w:
    df.to_excel(w,index=False,sheet_name="Open Positions")
wb=load_workbook(out)
ws=wb["Open Positions"]
headers={c.value:i+1 for i,c in enumerate(ws[1])}
for name in ("Mid","Mid Value"):
    if name in headers:
        col=headers[name]
        for row in range(2,ws.max_row+1):
            ws.cell(row,col).number_format='$#,##0.00'
wb.save(out)
print(out)
