TABLE = [
    63,
    -95,
    8,
    -44,
    98,
    -100,
    23,
    -27,
    75,
    122,
    -61,
    46,
    -111,
    86,
    -67,
    -16
]


def rotate_right8(value, count):
    value &= 0xff
    count &= 7

    if count == 0:
        return value

    return ((value << (8-count)) | (value >> count)) & 0xff


def keystream_byte(index, salt):
    return (TABLE[index % len(TABLE)] & 0xff) ^ salt[index % len(salt)]


def decode(encoded, salt):

    out=[]

    for i,b in enumerate(encoded):

        x = rotate_right8(
            b,
            (i % 7)+1
        )

        x ^= keystream_byte(i,salt)

        out.append(x)

    return bytes(out)



def unpack(blob):

    count = blob[0]

    records=[]

    pos=1

    for i in range(count):

        end = (
            ((blob[pos] & 0xff)<<8)
            |
            (blob[pos+1]&0xff)
        )

        start = pos+2

        pos=end+pos+2

        records.append(blob[start:pos])


    return records



with open("res/raw/messaging.bin","rb") as f:
    data=f.read()


records=unpack(data)

print("records:",len(records))


salt=b"onevoice-2026-W27"


plain=decode(records[1],salt)


print(plain.decode())

