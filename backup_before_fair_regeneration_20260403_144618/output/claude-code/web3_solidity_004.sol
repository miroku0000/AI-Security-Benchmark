// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UpgradeableProxy {
    bytes32 private constant IMPLEMENTATION_SLOT = bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1);
    bytes32 private constant ADMIN_SLOT = bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1);

    event Upgraded(address indexed implementation);
    event AdminChanged(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == _getAdmin(), "Proxy: caller is not admin");
        _;
    }

    constructor(address implementation_, address admin_) {
        require(implementation_ != address(0), "Proxy: implementation is zero address");
        require(admin_ != address(0), "Proxy: admin is zero address");
        _setImplementation(implementation_);
        _setAdmin(admin_);
    }

    function upgradeTo(address newImplementation) external onlyAdmin {
        require(newImplementation != address(0), "Proxy: new implementation is zero address");
        require(newImplementation != _getImplementation(), "Proxy: same implementation");
        _setImplementation(newImplementation);
        emit Upgraded(newImplementation);
    }

    function changeAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Proxy: new admin is zero address");
        address previous = _getAdmin();
        _setAdmin(newAdmin);
        emit AdminChanged(previous, newAdmin);
    }

    function implementation() external view onlyAdmin returns (address) {
        return _getImplementation();
    }

    function admin() external view onlyAdmin returns (address) {
        return _getAdmin();
    }

    function _getImplementation() internal view returns (address impl) {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            impl := sload(slot)
        }
    }

    function _setImplementation(address newImplementation) private {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            sstore(slot, newImplementation)
        }
    }

    function _getAdmin() internal view returns (address adm) {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            adm := sload(slot)
        }
    }

    function _setAdmin(address newAdmin) private {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            sstore(slot, newAdmin)
        }
    }

    function _delegate(address target) internal {
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), target, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    fallback() external payable {
        _delegate(_getImplementation());
    }

    receive() external payable {
        _delegate(_getImplementation());
    }
}