if (header.type == PACKET_POSITION) {
            if (static_cast<size_t>(received) < sizeof(PositionPacket)) {
                continue;
            }
            PositionPacket packet{};
            std::memcpy(&packet, buffer.data(), sizeof(packet));
            handlePositionPacket(sockfd, packet, clientAddr, players);
        } else if (header.type == PACKET_SHOOT) {
            if (static_cast<size_t>(received) < sizeof(ShootPacket)) {
                continue;
            }
            ShootPacket packet{};
            std::memcpy(&packet, buffer.data(), sizeof(packet));
            handleShootPacket(sockfd, packet, clientAddr, players);
        }
    }