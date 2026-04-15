use std::mem;

#[repr(C)]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub struct PacketHeader {
    pub version: u8,
    pub flags: u8,
    pub length: u16,
    pub seq: u32,
}

pub const PACKET_HEADER_BYTES: usize = mem::size_of::<PacketHeader>();

pub unsafe fn bytes_to_packet_header(bytes: &[u8; PACKET_HEADER_BYTES]) -> PacketHeader {
    mem::transmute(*bytes)
}

pub unsafe fn packet_header_to_bytes(header: &PacketHeader) -> [u8; PACKET_HEADER_BYTES] {
    mem::transmute(*header)
}

fn main() {
    let raw: [u8; PACKET_HEADER_BYTES] = [0x02, 0x01, 0x00, 0x40, 0x00, 0x00, 0x00, 0x01];
    unsafe {
        let hdr = bytes_to_packet_header(&raw);
        assert_eq!(packet_header_to_bytes(&hdr), raw);
    }
}
