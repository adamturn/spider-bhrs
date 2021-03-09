# standard library
import os
# python package index
import pandas as pd
# local modules
import path_helper
import pnc



def main():
    project = path_helper.ProjectPath.from_src(__file__)
    recovery_dir = project.root / "downloads/pnc"
    fnames = [name for name in os.listdir(recovery_dir) if os.path.isfile(str(recovery_dir / name))]

    print("Building DataFrames...")
    frames = []
    for fname in fnames:
        csv_path = str(recovery_dir / fname)
        frames.append(pd.read_csv(csv_path, sep=",", names=pnc.Record.columns))

    df = pd.concat(frames)
    export_path = project.root / "downloads/pnc.csv"
    print("Exporting final PNC CSV...")
    df.to_csv(export_path)

    return None


if __name__ == "__main__":
    main()