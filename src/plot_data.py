import pandas as pd
import matplotlib.pyplot as plt
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description="Plot stock data from CSV file")
parser.add_argument("--file", default="trading/data/LEVI/04_07_26.csv", 
                    help="Path to CSV file (default: trading/data/LEVI/04_07_26.csv)")
args = parser.parse_args()

# Read the CSV file
# The file has a multi-level header structure, so we need to skip the first 2 rows
df = pd.read_csv(args.file, skiprows=2)

# The columns are: Datetime, Close, High, Low, Open, Volume (after skipping header rows)
# 2nd column (index 1) = Close
# 5th column (index 4) = Open

# Convert Datetime to datetime object for better plotting
df['Datetime'] = pd.to_datetime(df['Datetime'])

# Get column names for labeling
x_column = df.columns[0]  # 1st column (Datetime)
y_column = df.columns[4]  # 5th column (Open)

# Create the plot
plt.figure(figsize=(12, 6))
plt.plot(df[x_column], df[y_column], linewidth=1, marker='o', markersize=2)
plt.xlabel(f'{x_column} Price ($)')
plt.ylabel(f'{y_column} Price ($)')
plt.title(f'AAPL Stock Data: {y_column} vs {x_column}')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Show the plot
plt.show()