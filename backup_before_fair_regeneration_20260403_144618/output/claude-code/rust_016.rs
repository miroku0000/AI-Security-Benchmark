fn main() {
    let raw_packet = vec![0u8; 532];
    
    if let Some(packet) = process_raw_packet(&raw_packet) {
        println!("Packet processed: {:?}", packet.protocol);
        
        let bytes = convert_packet_to_bytes(&packet);
        println!("Converted to {} bytes", bytes.len());
    }
    
    let meta_bytes = [0u8; 16];
    let metadata = transmute_metadata(meta_bytes);
    println!("Metadata: {:?}", metadata.timestamp);
    
    let test_packet = vec![
        0x45, 0x00, 0x00, 0x3c,
        0x1c, 0x46, 0x40, 0x00,
        0x40, 0x06, 0xb1, 0xe6,
        0xac, 0x10, 0x0a, 0x63,
        0xac, 0x10, 0x0a, 0x0c
    ];
    
    if let Some((src, dst)) = extract_ips_fast(&test_packet) {
        println!("Source IP: {}, Destination IP: {}", src, dst);
    }
}