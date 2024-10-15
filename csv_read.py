import csv

programmes = []
with open("jupas_university_programs_202408271511.csv", mode="r", encoding="utf8") as file:
    lines = csv.reader(file)
    for line in lines:
        programme = []
        programme.append(line[1])
        programme.append(line[3])
        programme.append(line[5])
        programme.append(line[16].split()[0])
        programmes.append(programme)
programmes = programmes[1:]
