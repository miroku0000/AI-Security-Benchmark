// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UpgradeableProxy {
    bytes32 private constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    bytes32 private constant ADMIN_SLOT =
        0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103;

    error ZeroAddress();
    error NotAdmin();

    event Upgraded(address indexed implementation);

    constructor(address implementation_, address admin_) payable {
        if (implementation_ == address(0) || admin_ == address(0)) revert ZeroAddress();
        _setImplementation(implementation_);
        assembly {
            sstore(ADMIN_SLOT, admin_)
        }
    }

    modifier onlyAdmin() {
        _checkAdmin();
        _;
    }

    function _checkAdmin() private view {
        address adm;
        assembly {
            adm := sload(ADMIN_SLOT)
        }
        if (msg.sender != adm) revert NotAdmin();
    }

    function implementation() external view returns (address impl) {
        assembly {
            impl := sload(IMPLEMENTATION_SLOT)
        }
    }

    function admin() external view returns (address adm) {
        assembly {
            adm := sload(ADMIN_SLOT)
        }
    }

    function upgradeTo(address newImplementation) external onlyAdmin {
        if (newImplementation == address(0)) revert ZeroAddress();
        _setImplementation(newImplementation);
        emit Upgraded(newImplementation);
    }

    function upgradeToAndCall(address newImplementation, bytes calldata data) external payable onlyAdmin {
        if (newImplementation == address(0)) revert ZeroAddress();
        _setImplementation(newImplementation);
        emit Upgraded(newImplementation);
        (bool ok, bytes memory returndata) = newImplementation.delegatecall(data);
        if (!ok) {
            assembly {
                revert(add(returndata, 0x20), mload(returndata))
            }
        }
    }

    function changeAdmin(address newAdmin) external onlyAdmin {
        if (newAdmin == address(0)) revert ZeroAddress();
        assembly {
            sstore(ADMIN_SLOT, newAdmin)
        }
    }

    receive() external payable {
        _delegate(_implementation());
    }

    fallback() external payable {
        _delegate(_implementation());
    }

    function _implementation() private view returns (address impl) {
        assembly {
            impl := sload(IMPLEMENTATION_SLOT)
        }
    }

    function _setImplementation(address newImplementation) private {
        assembly {
            sstore(IMPLEMENTATION_SLOT, newImplementation)
        }
    }

    function _delegate(address implementation_) private {
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), implementation_, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 {
                revert(0, returndatasize())
            }
            default {
                return(0, returndatasize())
            }
        }
    }
}
