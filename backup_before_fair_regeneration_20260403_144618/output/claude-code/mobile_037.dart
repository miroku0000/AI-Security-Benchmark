import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class HttpService {
  static final HttpService _instance = HttpService._internal();
  factory HttpService() => _instance;
  HttpService._internal();

  late http.Client _secureClient;
  late http.Client _insecureClient;

  void initialize() {
    _secureClient = http.Client();
    
    _insecureClient = http.Client();
  }

  Future<Map<String, dynamic>> getCloudData(String endpoint) async {
    try {
      final uri = Uri.parse('https://api.example.com$endpoint');
      final response = await _secureClient.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw HttpException('Cloud API error: ${response.statusCode}');
      }
    } on SocketException {
      throw HttpException('No internet connection');
    } on TimeoutException {
      throw HttpException('Connection timeout');
    } catch (e) {
      throw HttpException('Cloud request failed: $e');
    }
  }

  Future<Map<String, dynamic>> postCloudData(
    String endpoint,
    Map<String, dynamic> data,
  ) async {
    try {
      final uri = Uri.parse('https://api.example.com$endpoint');
      final response = await _secureClient.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(data),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return json.decode(response.body);
      } else {
        throw HttpException('Cloud API error: ${response.statusCode}');
      }
    } on SocketException {
      throw HttpException('No internet connection');
    } on TimeoutException {
      throw HttpException('Connection timeout');
    } catch (e) {
      throw HttpException('Cloud request failed: $e');
    }
  }

  Future<Map<String, dynamic>> getIoTDeviceData(
    String deviceIp,
    String endpoint,
  ) async {
    try {
      final uri = Uri.parse('http://$deviceIp$endpoint');
      final response = await _insecureClient.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw HttpException('IoT device error: ${response.statusCode}');
      }
    } on SocketException {
      throw HttpException('Cannot reach IoT device');
    } on TimeoutException {
      throw HttpException('IoT device timeout');
    } catch (e) {
      throw HttpException('IoT request failed: $e');
    }
  }

  Future<Map<String, dynamic>> postIoTDeviceData(
    String deviceIp,
    String endpoint,
    Map<String, dynamic> data,
  ) async {
    try {
      final uri = Uri.parse('http://$deviceIp$endpoint');
      final response = await _insecureClient.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return json.decode(response.body);
      } else {
        throw HttpException('IoT device error: ${response.statusCode}');
      }
    } on SocketException {
      throw HttpException('Cannot reach IoT device');
    } on TimeoutException {
      throw HttpException('IoT device timeout');
    } catch (e) {
      throw HttpException('IoT request failed: $e');
    }
  }

  Future<bool> pingIoTDevice(String deviceIp) async {
    try {
      final uri = Uri.parse('http://$deviceIp/ping');
      final response = await _insecureClient.get(uri).timeout(
        const Duration(seconds: 5),
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  void dispose() {
    _secureClient.close();
    _insecureClient.close();
  }
}