function upgradeToAndCall(address newImplementation, bytes calldata data) external payable onlyAdmin {
        _upgradeTo(newImplementation);
        (bool ok, bytes memory returndata) = newImplementation.delegatecall(data);
        if (!ok) {
            assembly {
                revert(add(returndata, 0x20), mload(returndata))
            }
        }
    }