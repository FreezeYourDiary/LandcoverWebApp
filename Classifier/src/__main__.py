from pipeline import run_analysis

if __name__ == "__main__":
    stats, outputs = run_analysis("data/real/raw2.jpg")
    print("Analysis complete.")
    print(stats)
