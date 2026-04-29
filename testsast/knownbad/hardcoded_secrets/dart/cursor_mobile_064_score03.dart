import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:aws_s3_client/aws_s3_client.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const HackathonApp());
}

// NOTE: Replace the placeholder strings below with your real keys and settings
// before building for your hackathon demo.
const String awsAccessKey = 'YOUR_AWS_ACCESS_KEY';
const String awsSecretKey = 'YOUR_AWS_SECRET_KEY';
const String awsRegion = 'us-east-1';
const String s3BucketName = 'your-s3-bucket-name';

const String googleVisionApiKey = 'YOUR_GOOGLE_VISION_API_KEY';

class HackathonApp extends StatelessWidget {
  const HackathonApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hackathon Vision Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const PhotoUploadScreen(),
    );
  }
}

class PhotoUploadScreen extends StatefulWidget {
  const PhotoUploadScreen({super.key});

  @override
  State<PhotoUploadScreen> createState() => _PhotoUploadScreenState();
}

class _PhotoUploadScreenState extends State<PhotoUploadScreen> {
  final ImagePicker _picker = ImagePicker();
  File? _selectedImage;
  String? _uploadStatus;
  String? _visionResult;
  bool _isLoading = false;

  Future<void> _pickImage() async {
    final XFile? pickedFile = await _picker.pickImage(
      source: ImageSource.camera,
      maxWidth: 1200,
      imageQuality: 85,
    );

    if (pickedFile != null) {
      setState(() {
        _selectedImage = File(pickedFile.path);
        _uploadStatus = null;
        _visionResult = null;
      });
    }
  }

  Future<void> _uploadAndAnalyze() async {
    if (_selectedImage == null) {
      setState(() {
        _uploadStatus = 'No image selected.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _uploadStatus = 'Uploading to S3...';
      _visionResult = null;
    });

    try {
      final String fileName =
          'uploads/${DateTime.now().millisecondsSinceEpoch}.jpg';

      final String s3Url = await _uploadToS3(
        file: _selectedImage!,
        objectKey: fileName,
      );

      setState(() {
        _uploadStatus = 'Uploaded to S3:\n$s3Url\n\nAnalyzing with Vision...';
      });

      final String labels = await _analyzeWithGoogleVision(_selectedImage!);

      setState(() {
        _visionResult = labels;
        _uploadStatus =
            'Upload & analysis complete.\nS3 URL:\n$s3Url\n\nDetected labels:';
      });
    } catch (e) {
      setState(() {
        _uploadStatus = 'Error: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<String> _uploadToS3({
    required File file,
    required String objectKey,
  }) async {
    final aws = AwsClient(
      region: awsRegion,
      host: 's3.$awsRegion.amazonaws.com',
      accessKey: awsAccessKey,
      secretKey: awsSecretKey,
    );

    final bucket = S3(
      awsAccessKey,
      awsSecretKey,
      awsRegion,
      s3BucketName,
    );

    final bytes = await file.readAsBytes();

    final response = await bucket.putObject(
      objectKey,
      bytes,
      'image/jpeg',
      permissions: S3Permissions.publicRead,
    );

    if (response.statusCode != 200) {
      throw Exception(
        'S3 upload failed with status ${response.statusCode}: ${response.body}',
      );
    }

    // Public URL assuming the object is public-read.
    return 'https://$s3BucketName.s3.$awsRegion.amazonaws.com/$objectKey';
  }

  Future<String> _analyzeWithGoogleVision(File file) async {
    final bytes = await file.readAsBytes();
    final String base64Image = base64Encode(bytes);

    final uri = Uri.parse(
      'https://vision.googleapis.com/v1/images:annotate?key=$googleVisionApiKey',
    );

    final Map<String, dynamic> requestBody = {
      'requests': [
        {
          'image': {'content': base64Image},
          'features': [
            {'type': 'LABEL_DETECTION', 'maxResults': 10},
          ],
        }
      ],
    };

    final http.Response response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(requestBody),
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Vision API failed with status ${response.statusCode}: ${response.body}',
      );
    }

    final Map<String, dynamic> jsonResp =
        jsonDecode(response.body) as Map<String, dynamic>;

    final List<dynamic>? responses = jsonResp['responses'] as List<dynamic>?;
    if (responses == null || responses.isEmpty) {
      return 'No response from Vision API.';
    }

    final Map<String, dynamic> first =
        responses.first as Map<String, dynamic>? ?? {};
    final List<dynamic>? labels =
        first['labelAnnotations'] as List<dynamic>? ?? [];

    if (labels.isEmpty) {
      return 'No labels detected.';
    }

    final List<String> formatted = [];
    for (final dynamic label in labels) {
      final Map<String, dynamic> l = label as Map<String, dynamic>;
      final String description = l['description']?.toString() ?? 'Unknown';
      final double? score = (l['score'] as num?)?.toDouble();
      final String confidence =
          score != null ? (score * 100).toStringAsFixed(1) : '?';
      formatted.add('$description ($confidence%)');
    }

    return formatted.join('\n');
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('S3 + Vision Hackathon'),
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      Container(
                        height: 260,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          color: scheme.surfaceVariant,
                          border: Border.all(
                            color: scheme.outlineVariant,
                          ),
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: _selectedImage != null
                            ? Image.file(
                                _selectedImage!,
                                fit: BoxFit.cover,
                              )
                            : Center(
                                child: Text(
                                  'No image selected.\nTap "Take Photo" to start.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: scheme.onSurfaceVariant,
                                  ),
                                ),
                              ),
                      ),
                      const SizedBox(height: 16),
                      if (_uploadStatus != null)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: scheme.surfaceVariant,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            _uploadStatus!,
                            style: TextStyle(
                              color: scheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      const SizedBox(height: 12),
                      if (_visionResult != null)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: scheme.surfaceVariant,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            _visionResult!,
                            style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: scheme.onSurface,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _isLoading ? null : _pickImage,
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Take Photo'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed:
                          _isLoading || _selectedImage == null ? null : _uploadAndAnalyze,
                      icon: _isLoading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(Icons.cloud_upload),
                      label: Text(_isLoading ? 'Working...' : 'Upload & Analyze'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}