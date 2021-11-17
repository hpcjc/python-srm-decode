"""
This Python code is a port of the GoldenCheetah SrmRideFile.cpp.
https://github.com/GoldenCheetah/GoldenCheetah
"""
import math
from datetime import date, timedelta, datetime, time
from struct import unpack
from typing import BinaryIO, Union


class UnrecognizedFileType(Exception):
    pass


class UnsupportedFormatVersion(Exception):
    pass


class Marker:
    start: int
    end: int
    note: str

    def __init__(self, start: int = 0, end: int = 0, note: str = None):
        self.start = start
        self.end = end
        self.note = note


class BlockHeader:
    chunk_count: int
    timestamp: datetime


class Record:
    timestamp: datetime
    seconds: float
    cadence: int
    heart_rate: int
    km: float
    kph: float
    nm: float
    watts: int
    altitude: float
    longitude: float
    latitude: float
    temperature: float
    interval: int

    def __init__(self,
                 timestamp: datetime,
                 seconds: float,
                 cadence: int,
                 heart_rate: int,
                 km: float,
                 kph: float,
                 nm: float,
                 watts: int,
                 altitude: float,
                 longitude: float,
                 latitude: float,
                 temperature: float,
                 interval: int):
        self.timestamp = timestamp
        self.seconds = seconds
        self.cadence = cadence
        self.heart_rate = heart_rate
        self.km = km
        self.kph = kph
        self.nm = nm
        self.watts = watts
        self.altitude = altitude
        self.longitude = longitude
        self.latitude = latitude
        self.temperature = temperature
        self.interval = interval

    def __repr__(self):
        return (f'<Record'
                f' seconds={self.seconds:.2f},'
                f' cadence={self.cadence},'
                f' heart_rate={self.heart_rate},'
                f' km={self.km:.1f},'
                f' kph={self.kph:.2f},'
                f' nm={self.nm:.2f},'
                f' watts={self.watts},'
                f' altitude={self.altitude},'
                f' longitude={self.longitude},'
                f' latitude={self.latitude},'
                f' temperature={self.temperature},'
                f' interval={self.interval},'
                f' timestamp={repr(self.timestamp)}>')


class Parser:
    in_: BinaryIO
    notes: str
    recording_interval: float
    wheel_circumference: int
    date: date
    athlete_name: str
    start_time: Union[datetime, None]
    records: [Record]
    zero_offset: int
    slope: float

    def __init__(self):
        self.recording_interval = 1.0
        self.wheel_circumference = 2093
        self.date = date(1880, 1, 1)
        self.start_time = None
        self.records = []
        self.zero_offset = 500
        self.slope = 25.0

    def open_file(self, path: str):
        self.in_ = open(path, 'rb')

    def read_raw(self, size: int) -> bytes:
        return self.in_.read(size)

    def read_byte(self) -> int:
        result, *_ = unpack('<B', self.in_.read(1))
        return result

    def read_short(self) -> int:
        result, *_ = unpack('<H', self.in_.read(2))
        return result

    def read_signed_short(self) -> int:
        result, *_ = unpack('<h', self.in_.read(2))
        return result

    def read_long(self) -> int:
        result, *_ = unpack('<L', self.in_.read(4))
        return result

    def read_signed_long(self) -> int:
        result, *_ = unpack('<l', self.in_.read(4))
        return result

    def parse(self):
        magic = self.read_raw(4)
        if magic[:3] != b'SRM':
            raise UnrecognizedFileType('missing magic')
        version = magic[3] - 0x30  # ascii to int
        if version not in (5, 6, 7, 9):
            raise UnsupportedFormatVersion(
                f'unsupported SRM file format version: {version}')

        self.date = self.date + timedelta(days=self.read_short())
        self.wheel_circumference = self.read_short()
        recording_interval1 = self.read_byte()
        recording_interval2 = self.read_byte()
        self.recording_interval = recording_interval1 / recording_interval2
        recording_interval_mseconds = round(self.recording_interval * 1000.0)
        block_count = self.read_short()
        marker_count = self.read_short()
        _ = self.read_byte()  # skip padding

        _ = self.read_byte()  # skip comment length
        comment = self.read_raw(70)
        self.notes = comment.decode('UTF-8')

        markers = []
        comment_length = 255
        if version < 6:
            comment_length = 3
        for _ in range(0, marker_count + 1):
            comment = self.read_raw(comment_length)
            _ = self.read_byte()  # skip active
            if version < 9:
                start = self.read_short()
                end = self.read_short()
            else:
                start = self.read_long()
                end = self.read_short()
            _ = self.read_short()  # skip mean watts
            _ = self.read_short()  # skip mean heart rate
            _ = self.read_short()  # skip mean cadence
            _ = self.read_short()  # skip mean speed
            _ = self.read_short()  # skip PWC150
            if start < 1:
                start = 1
            if end < 1:
                end = 1

            marker = Marker()
            if end < start:
                marker.start = end
                marker.end = start
            else:
                marker.start = start
                marker.end = end
            marker.note = comment.decode('UTF-8')
            if len(markers) == 0:
                self.athlete_name = marker.note
            markers.append(marker)

        block_chunk_count = 0
        block_headers = []
        for _ in range(0, block_count):
            seconds_since_noon = self.read_long()
            block_header = BlockHeader()
            if version < 9:
                block_header.chunk_count = self.read_short()
            else:
                block_header.chunk_count = self.read_long()
            block_header.timestamp = datetime.combine(self.date, time())
            block_header.timestamp += timedelta(
                seconds=seconds_since_noon * 10)
            block_chunk_count += block_header.chunk_count
            block_headers.append(block_header)

        self.zero_offset = self.read_short()
        slope = self.read_short()
        self.slope = round(140.0 / 42781 * slope, 2)

        if version < 9:
            chunk_count = self.read_short()
        else:
            chunk_count = self.read_long()
        _ = self.read_byte()  # padding

        # SRM5 files have no blocks - synthesize one
        if block_count < 1:
            block_count = 0
            block_header = BlockHeader()
            block_header.chunk_count = chunk_count
            block_header.timestamp = datetime.combine(self.date, time())
            block_headers.append(block_header)
        if chunk_count > block_chunk_count:
            block_chunk_count = chunk_count

        block_index = 0
        block_num = 0
        marker_num = 0
        interval = 0
        km = 0.0
        secs = 0.0
        if marker_count > 0:
            marker_num = 1

        for i in range(0, block_chunk_count):
            if version < 7:
                ps = self.read_raw(3)
                cad = self.read_byte()
                hr = self.read_byte()
                kph = (((ps[1] & 0xf0) << 3) | (ps[0] & 0x7f)) * 3.0 / 26.0
                watts = (ps[1] & 0x0f) | (ps[2] << 0x4)
                altitude = 0.0
                temperature = None
                latitude = longitude = None
            else:
                watts = self.read_short()
                cad = self.read_byte()
                hr = self.read_byte()

                kph_tmp = self.read_signed_long()
                kph = 0
                if kph_tmp > 0:
                    kph = round(kph_tmp * 3.6 / 1000.0, 4)
                altitude = self.read_signed_long()
                temperature = 0.1 * self.read_signed_short()
                if version == 9:
                    latitude = self.read_signed_long() * 180.0 / 0x7fffffff
                    longitude = self.read_signed_long() * 180.0 / 0x7fffffff
                else:
                    latitude = longitude = None

            if not self.start_time:
                self.start_time = block_headers[block_num].timestamp
            if marker_num < len(markers) and i == markers[marker_num].end:
                interval += 1
                marker_num += 1

            is_markers_count_from_1 = (i > 0
                                       and marker_num < len(markers)
                                       and i == markers[marker_num].start - 1)
            if is_markers_count_from_1:
                interval += 1

            km += round(recording_interval_mseconds * kph / 3600.0, 4)
            if cad:
                nm = round(watts / 2.0 / math.pi / cad * 60.0, 4)
            else:
                nm = 0.0

            timestamp = block_headers[block_num].timestamp\
                + timedelta(seconds=secs)
            record = Record(seconds=secs,
                            cadence=cad,
                            heart_rate=hr,
                            km=km,
                            kph=kph,
                            nm=nm,
                            watts=watts,
                            altitude=altitude,
                            temperature=temperature,
                            latitude=latitude,
                            longitude=longitude,
                            timestamp=timestamp,
                            interval=interval)
            self.records.append(record)

            block_index += 1
            if (block_index == block_headers[block_num].chunk_count
                    and block_num + 1 < block_count):
                duration = recording_interval_mseconds\
                    * block_headers[block_num].chunk_count
                end = block_headers[block_num].timestamp\
                    + timedelta(seconds=duration)
                block_num += 1
                block_index = 0
                start = block_headers[block_num].timestamp
                diff_secs = (end - start).total_seconds()
                if diff_secs < self.recording_interval:
                    secs += self.recording_interval
                else:
                    secs += diff_secs
            else:
                secs += self.recording_interval

