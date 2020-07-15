import time
import datetime
import statistics

files = ['1delay-e2e.txt', '5delay-e2e.txt', '10delay-e2e.txt', '15delay-e2e.txt', '20delay-e2e.txt']

for e2e_file in files:

    durations = []
    with open(e2e_file) as fp:
        for line in fp:
            day = line.split(" ")[0]
            recv = "{} {}".format(day, line.split(" ")[1])
            recv = datetime.datetime.strptime(recv, '%Y-%m-%d %H:%M:%S.%f')
            send = "{} {}".format(day, line.split(" ")[3][:-1])
            send = datetime.datetime.strptime(send, '%Y-%m-%d %H:%M:%S.%f')

            durations.append((recv - send).total_seconds())

    print(durations)
    print(statistics.variance(durations), statistics.mean(durations), statistics.median(durations))
