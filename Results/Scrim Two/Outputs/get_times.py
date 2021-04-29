import glob


for fp in glob.iglob("*/agent_*.txt"):
    with open(fp) as f:
        lines = f.read().splitlines()
    times = []
    for line in lines:
        if "TIME: " in line:
            line = line[line.find("TIME: "):-1]
            line = float(line[6:])
            times.append(line)
    print(fp, max(times))