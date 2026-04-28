// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UpgradeableProxy {
    bytes32 private constant IMPLEMENTATION_SLOT = keccak256("eip1967.proxy.implementation");
    bytes32 private constant ADMIN_SLOT = keccak256("eip1967.proxy.admin");

    event Upgraded(address indexed implementation);
    event AdminChanged(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == _getAdmin(), "UpgradeableProxy: caller is not the admin");
        _;
    }

    constructor(address implementation, address admin) {
        _setImplementation(implementation);
        _setAdmin(admin);
    }

    fallback() external payable {
        _delegate(_getImplementation());
    }

    receive() external payable {}

    function upgradeTo(address newImplementation) public onlyAdmin {
        require(newImplementation != address(0), "UpgradeableProxy: invalid implementation");
        _setImplementation(newImplementation);
        emit Upgraded(newImplementation);
    }

    function upgradeToAndCall(address newImplementation, bytes calldata data) public payable onlyAdmin {
        upgradeTo(newImplementation);
        (bool success, ) = newImplementation.delegatecall(data);
        require(success, "UpgradeableProxy: delegatecall failed");
    }

    function changeAdmin(address newAdmin) public onlyAdmin {
        require(newAdmin != address(0), "UpgradeableProxy: invalid admin");
        address previousAdmin = _getAdmin();
        _setAdmin(newAdmin);
        emit AdminChanged(previousAdmin, newAdmin);
    }

    function getImplementation() public view returns (address) {
        return _getImplementation();
    }

    function getAdmin() public view returns (address) {
        return _getAdmin();
    }

    function _delegate(address implementation) internal {
        assembly {
            calldatasize := calldatasize()
            calldatacopy(0, 0, calldatasize)
            let result := delegatecall(gas(), implementation, 0, calldatasize, 0, 0)
            returndatasize := returndatasize()
            returndatacopy(0, 0, returndatasize)
            switch result
            case 0 {
                revert(0, returndatasize)
            }
            default {
                return(0, returndatasize)
            }
        }
    }

    function _getImplementation() internal view returns (address impl) {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            impl := sload(slot)
        }
    }

    function _setImplementation(address newImplementation) internal {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            sstore(slot, newImplementation)
        }
    }

    function _getAdmin() internal view returns (address admin) {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            admin := sload(slot)
        }
    }

    function _setAdmin(address newAdmin) internal {
        bytes32 slot = ADMIN_SLOT;
        assembly {
            sstore(slot, newAdmin)
        }
    }
}

contract ProxyAdmin {
    mapping(address => address) public proxyToAdmin;

    event ProxyCreated(address indexed proxy, address indexed implementation, address indexed admin);

    function createProxy(address implementation, bytes memory initData) public returns (address) {
        UpgradeableProxy proxy = new UpgradeableProxy(implementation, msg.sender);
        proxyToAdmin[address(proxy)] = msg.sender;

        if (initData.length > 0) {
            (bool success, ) = address(proxy).call(initData);
            require(success, "ProxyAdmin: initialization failed");
        }

        emit ProxyCreated(address(proxy), implementation, msg.sender);
        return address(proxy);
    }

    function upgrade(address proxy, address newImplementation) public {
        require(proxyToAdmin[proxy] == msg.sender, "ProxyAdmin: not authorized");
        UpgradeableProxy(proxy).upgradeTo(newImplementation);
    }

    function upgradeAndCall(address proxy, address newImplementation, bytes memory data) public payable {
        require(proxyToAdmin[proxy] == msg.sender, "ProxyAdmin: not authorized");
        UpgradeableProxy(proxy).upgradeToAndCall(newImplementation, data);
    }
}

contract ImplementationV1 {
    uint256 public value;
    string public name;

    function initialize(string memory _name, uint256 _value) public {
        name = _name;
        value = _value;
    }

    function setValue(uint256 _value) public {
        value = _value;
    }

    function getValue() public view returns (uint256) {
        return value;
    }

    function getName() public view returns (string memory) {
        return name;
    }

    function increment() public {
        value += 1;
    }
}

contract ImplementationV2 is ImplementationV1 {
    uint256 public multiplier;

    function setMultiplier(uint256 _multiplier) public {
        multiplier = _multiplier;
    }

    function getValueWithMultiplier() public view returns (uint256) {
        return value * multiplier;
    }

    function incrementByMultiplier() public {
        value += multiplier;
    }
}