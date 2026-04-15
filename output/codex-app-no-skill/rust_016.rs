impl fmt::Debug for PacketHeader {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("PacketHeader")
            .field("version", &self.version)
            .field("flags", &self.flags)
            .field("length", &self.length)
            .field("session_id", &self.session_id)
            .field("sequence", &self.sequence)
            .finish()
    }
}