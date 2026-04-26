use std::mem::transmute;

const HEADER_SIZE: usize = 16;

#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct PacketHeader {
    version: u8,
    flags: u8,
    payload_len_be: [u8; 2],
    session_id_be: [u8; 4],
    sequence_be: [u8; 4],
    checksum_be: [u8; 4],
}

impl PacketHeader {
    #[inline(always)]
    fn payload_len(self) -> u16 {
        u16::from_be_bytes(self.payload_len_be)
    }

    #[inline(always)]
    fn session_id(self) -> u32 {
        u32::from_be_bytes(self.session_id_be)
    }

    #[inline(always)]
    fn sequence(self) -> u32 {
        u32::from_be_bytes(self.sequence_be)
    }

    #[inline(always)]
    fn checksum(self) -> u32 {
        u32::from_be_bytes(self.checksum_be)
    }

    #[inline(always)]
    fn as_bytes(self) -> [u8; HEADER_SIZE] {
        unsafe { transmute(self) }
    }
}

#[inline(always)]
fn bytes_to_header(bytes: [u8; HEADER_SIZE]) -> PacketHeader {
    unsafe { transmute(bytes) }
}

#[derive(Debug)]
struct ParsedPacket<'a> {
    header: PacketHeader,
    payload: &'a [u8],
}

#[inline(always)]
fn parse_packet(packet: &[u8]) -> Option<ParsedPacket<'_>> {
    if packet.len() < HEADER_SIZE {
        return None;
    }

    let header_bytes: [u8; HEADER_SIZE] = packet[..HEADER_SIZE].try_into().ok()?;
    let header = bytes_to_header(header_bytes);
    let payload_len = header.payload_len() as usize;

    if packet.len() != HEADER_SIZE + payload_len {
        return None;
    }

    Some(ParsedPacket {
        header,
        payload: &packet[HEADER_SIZE..],
    })
}

#[inline(always)]
fn build_packet(
    version: u8,
    flags: u8,
    session_id: u32,
    sequence: u32,
    payload: &[u8],
) -> Vec<u8> {
    let checksum = payload
        .iter()
        .fold(0u32, |acc, &b| acc.wrapping_add(b as u32));

    let header = PacketHeader {
        version,
        flags,
        payload_len_be: (payload.len() as u16).to_be_bytes(),
        session_id_be: session_id.to_be_bytes(),
        sequence_be: sequence.to_be_bytes(),
        checksum_be: checksum.to_be_bytes(),
    };

    let mut out = Vec::with_capacity(HEADER_SIZE + payload.len());
    out.extend_from_slice(&header.as_bytes());
    out.extend_from_slice(payload);
    out
}

fn main() {
    let payload = b"hello-packet";
    let packet = build_packet(1, 0b1010_0001, 0x11223344, 42, payload);
    let parsed = parse_packet(&packet).expect("valid packet");

    assert_eq!(parsed.header.version, 1);
    assert_eq!(parsed.header.flags, 0b1010_0001);
    assert_eq!(parsed.header.payload_len(), payload.len() as u16);
    assert_eq!(parsed.header.session_id(), 0x11223344);
    assert_eq!(parsed.header.sequence(), 42);
    assert_eq!(
        parsed.header.checksum(),
        payload.iter().fold(0u32, |acc, &b| acc.wrapping_add(b as u32))
    );
    assert_eq!(parsed.payload, payload);

    println!("{parsed:?}");
}