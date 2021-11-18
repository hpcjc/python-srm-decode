import argparse

from srmdecode import Decoder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="The .srm file you want to decode")
    args = parser.parse_args()

    with open(args.file, 'rb') as f:
        decoder = Decoder()
        records = decoder.decode(f)
        print(('Time,Speed [km/h],Power [watt],Cadence,Heartrate,'
               'Temperature [℃],Altitude [m],latitude,longitude'))
        for record in records:
            # CSV format by SRMX software
            print((f'{record.timestamp.strftime("%F %H:%M:%S")},'
                   f'{record.kph:.1f},{record.watts:.1f},{record.cadence:.1f},'
                   f'{record.heartrate:.1f},{record.temperature:.1f},'
                   f'{record.altitude:.1f},{record.latitude},{record.longitude}'))


if __name__ == '__main__':
    main()
