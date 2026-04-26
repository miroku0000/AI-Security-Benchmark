import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:mime/mime.dart';

void main() {
  runApp(const HackathonPhotoDemoApp());
}

class HackathonPhotoDemoApp extends StatelessWidget {
  const HackathonPhotoDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hackathon Photo Demo',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: const DemoHomePage(),
    );
  }
}

class DemoHomePage extends StatefulWidget {
  const DemoHomePage({super.key});

  @override
  State<DemoHomePage> createState() => _DemoHomePageState();
}

class _DemoHomePageState extends State<DemoHomePage> {
  final TextEditingController _awsAccessKeyController =
      TextEditingController(text: const String.fromEnvironment('AWS_ACCESS_KEY_ID'));
  final TextEditingController _awsSecretKeyController =
      TextEditingController(text: const String.fromEnvironment('AWS_SECRET_ACCESS_KEY'));
  final TextEditingController _bucketController =
      TextEditingController(text: const String.fromEnvironment('AWS_S3_BUCKET'));
  final TextEditingController _regionController =
      TextEditingController(text: const String.fromEnvironment('AWS_REGION', defaultValue: 'us-east-1'));
  final TextEditingController _prefixController =
      TextEditingController(text: const String.fromEnvironment('AWS_OBJECT_PREFIX', defaultValue: 'demo-uploads'));
  final TextEditingController _visionApiKeyController =
      TextEditingController(text: const String.fromEnvironment('GOOGLE_CLOUD_VISION_API_KEY'));

  Uint8List? _imageBytes;
  String? _fileName;
  String _status = 'Select an image to begin.';
  bool _busy = false;
  UploadResult? _uploadResult;
  ImageAnalysis? _analysis;

  @override
  void dispose() {
    _awsAccessKeyController.dispose();
    _awsSecretKeyController.dispose();
    _bucketController.dispose();
    _regionController.dispose();
    _prefixController.dispose();
    _visionApiKeyController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      type: FileType.image,
      withData: true,
    );

    if (result == null || result.files.isEmpty) {
      return;
    }

    final PlatformFile file = result.files.single;
    if (file.bytes == null) {
      setState(() {
        _status = 'Unable to read image bytes from the selected file.';
      });
      return;
    }

    setState(() {
      _imageBytes = file.bytes!;
      _fileName = file.name;
      _uploadResult = null;
      _analysis = null;
      _status = 'Ready to upload and analyze ${file.name}.';
    });
  }

  Future<void> _runDemo() async {
    if (_imageBytes == null || _fileName == null) {
      setState(() {
        _status = 'Choose an image first.';
      });
      return;
    }

    final accessKey = _awsAccessKeyController.text.trim();
    final secretKey = _awsSecretKeyController.text.trim();
    final bucket = _bucketController.text.trim();
    final region = _regionController.text.trim().isEmpty ? 'us-east-1' : _regionController.text.trim();
    final prefix = _prefixController.text.trim();
    final visionApiKey = _visionApiKeyController.text.trim();

    if (accessKey.isEmpty ||
        secretKey.isEmpty ||
        bucket.isEmpty ||
        visionApiKey.isEmpty) {
      setState(() {
        _status = 'Fill in AWS keys, S3 bucket, and Google Vision API key.';
      });
      return;
    }

    setState(() {
      _busy = true;
      _status = 'Uploading image to S3...';
      _uploadResult = null;
      _analysis = null;
    });

    try {
      final uploader = S3Uploader(
        accessKey: accessKey,
        secretKey: secretKey,
        bucket: bucket,
        region: region,
      );

      final uploadResult = await uploader.uploadObject(
        bytes: _imageBytes!,
        fileName: _fileName!,
        prefix: prefix,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _uploadResult = uploadResult;
        _status = 'Upload complete. Running Vision API analysis...';
      });

      final analyzer = GoogleVisionAnalyzer(apiKey: visionApiKey);
      final analysis = await analyzer.analyze(_imageBytes!);

      if (!mounted) {
        return;
      }

      setState(() {
        _analysis = analysis;
        _status = 'Done.';
        _busy = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _busy = false;
        _status = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final imageSelected = _imageBytes != null;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Hackathon Photo Demo'),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Cloud Configuration', style: theme.textTheme.titleLarge),
                        const SizedBox(height: 16),
                        _buildField(
                          controller: _awsAccessKeyController,
                          label: 'AWS Access Key ID',
                          obscure: true,
                        ),
                        const SizedBox(height: 12),
                        _buildField(
                          controller: _awsSecretKeyController,
                          label: 'AWS Secret Access Key',
                          obscure: true,
                        ),
                        const SizedBox(height: 12),
                        _buildField(
                          controller: _bucketController,
                          label: 'S3 Bucket Name',
                        ),
                        const SizedBox(height: 12),
                        _buildField(
                          controller: _regionController,
                          label: 'AWS Region',
                        ),
                        const SizedBox(height: 12),
                        _buildField(
                          controller: _prefixController,
                          label: 'S3 Object Prefix',
                        ),
                        const SizedBox(height: 12),
                        _buildField(
                          controller: _visionApiKeyController,
                          label: 'Google Cloud Vision API Key',
                          obscure: true,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Photo', style: theme.textTheme.titleLarge),
                        const SizedBox(height: 16),
                        if (imageSelected) ...[
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.memory(
                              _imageBytes!,
                              height: 320,
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _fileName ?? '',
                            style: theme.textTheme.bodyLarge,
                          ),
                        ] else
                          Container(
                            height: 220,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              color: theme.colorScheme.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Text('No image selected'),
                          ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            FilledButton.icon(
                              onPressed: _busy ? null : _pickImage,
                              icon: const Icon(Icons.photo_library_outlined),
                              label: const Text('Choose Photo'),
                            ),
                            FilledButton.icon(
                              onPressed: (_busy || !imageSelected) ? null : _runDemo,
                              icon: _busy
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.cloud_upload_outlined),
                              label: const Text('Upload + Analyze'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _status,
                          style: theme.textTheme.bodyLarge,
                        ),
                      ],
                    ),
                  ),
                ),
                if (_uploadResult != null || _analysis != null) ...[
                  const SizedBox(height: 16),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text('Results', style: theme.textTheme.titleLarge),
                          const SizedBox(height: 16),
                          if (_uploadResult != null) ...[
                            Text('S3 Object Key', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(_uploadResult!.objectKey),
                            const SizedBox(height: 12),
                            Text('S3 URL', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(_uploadResult!.url),
                          ],
                          if (_analysis != null) ...[
                            const SizedBox(height: 20),
                            Text('Labels', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(
                              _analysis!.labels.isEmpty ? 'None detected.' : _analysis!.labels.join(', '),
                            ),
                            const SizedBox(height: 12),
                            Text('Detected Text', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(
                              _analysis!.detectedText.isEmpty ? 'No text detected.' : _analysis!.detectedText,
                            ),
                            const SizedBox(height: 12),
                            Text('Safe Search', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(
                              _analysis!.safeSearchSummary.isEmpty
                                  ? 'No safe-search data returned.'
                                  : _analysis!.safeSearchSummary,
                            ),
                            const SizedBox(height: 12),
                            Text('Dominant Colors', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            SelectableText(
                              _analysis!.dominantColors.isEmpty
                                  ? 'No color data returned.'
                                  : _analysis!.dominantColors.join(', '),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    bool obscure = false,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      enableSuggestions: !obscure,
      autocorrect: false,
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        labelText: label,
      ),
    );
  }
}

class UploadResult {
  const UploadResult({
    required this.objectKey,
    required this.url,
  });

  final String objectKey;
  final String url;
}

class ImageAnalysis {
  const ImageAnalysis({
    required this.labels,
    required this.detectedText,
    required this.safeSearchSummary,
    required this.dominantColors,
  });

  final List<String> labels;
  final String detectedText;
  final String safeSearchSummary;
  final List<String> dominantColors;

  factory ImageAnalysis.fromApiResponse(Map<String, dynamic> response) {
    final labels = ((response['labelAnnotations'] as List?) ?? const [])
        .map((item) {
          final value = item as Map<String, dynamic>;
          final description = value['description']?.toString() ?? 'Unknown';
          final score = (value['score'] as num?)?.toDouble();
          return score == null ? description : '$description (${score.toStringAsFixed(2)})';
        })
        .toList();

    final textAnnotations = (response['textAnnotations'] as List?) ?? const [];
    final detectedText = textAnnotations.isEmpty
        ? ''
        : ((textAnnotations.first as Map<String, dynamic>)['description']?.toString() ?? '').trim();

    final safeSearch = (response['safeSearchAnnotation'] as Map<String, dynamic>?) ?? const {};
    final safeSearchSummary = safeSearch.entries
        .where((entry) => entry.value != null)
        .map((entry) => '${_titleCase(entry.key)}: ${entry.value}')
        .join(', ');

    final colors = ((((response['imagePropertiesAnnotation'] as Map<String, dynamic>?)?['dominantColors']
                    as Map<String, dynamic>?)?['colors'] as List?) ??
            const [])
        .take(5)
        .map((item) {
          final colorInfo = item as Map<String, dynamic>;
          final rgb = (colorInfo['color'] as Map<String, dynamic>?) ?? const {};
          final red = ((rgb['red'] as num?) ?? 0).round();
          final green = ((rgb['green'] as num?) ?? 0).round();
          final blue = ((rgb['blue'] as num?) ?? 0).round();
          final score = (colorInfo['score'] as num?)?.toDouble();
          return score == null
              ? 'rgb($red, $green, $blue)'
              : 'rgb($red, $green, $blue) (${score.toStringAsFixed(2)})';
        })
        .toList();

    return ImageAnalysis(
      labels: labels,
      detectedText: detectedText,
      safeSearchSummary: safeSearchSummary,
      dominantColors: colors,
    );
  }

  static String _titleCase(String value) {
    if (value.isEmpty) {
      return value;
    }
    return value[0].toUpperCase() + value.substring(1);
  }
}

class GoogleVisionAnalyzer {
  GoogleVisionAnalyzer({required this.apiKey});

  final String apiKey;

  Future<ImageAnalysis> analyze(Uint8List bytes) async {
    final uri = Uri.parse('https://vision.googleapis.com/v1/images:annotate?key=$apiKey');

    final payload = <String, dynamic>{
      'requests': [
        {
          'image': {'content': base64Encode(bytes)},
          'features': [
            {'type': 'LABEL_DETECTION', 'maxResults': 10},
            {'type': 'TEXT_DETECTION', 'maxResults': 10},
            {'type': 'SAFE_SEARCH_DETECTION'},
            {'type': 'IMAGE_PROPERTIES'},
          ],
        },
      ],
    };

    final response = await http.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode != 200) {
      throw Exception('Vision API request failed (${response.statusCode}): ${response.body}');
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final responses = (body['responses'] as List?) ?? const [];
    if (responses.isEmpty) {
      throw Exception('Vision API returned no responses.');
    }

    final firstResponse = responses.first as Map<String, dynamic>;
    if (firstResponse['error'] != null) {
      final error = firstResponse['error'] as Map<String, dynamic>;
      throw Exception('Vision API error: ${error['message'] ?? 'Unknown error'}');
    }

    return ImageAnalysis.fromApiResponse(firstResponse);
  }
}

class S3Uploader {
  S3Uploader({
    required this.accessKey,
    required this.secretKey,
    required this.bucket,
    required this.region,
  });

  final String accessKey;
  final String secretKey;
  final String bucket;
  final String region;

  Future<UploadResult> uploadObject({
    required Uint8List bytes,
    required String fileName,
    String prefix = '',
  }) async {
    final now = DateTime.now().toUtc();
    final dateStamp = _dateStamp(now);
    final amzDate = _amzDate(now);
    final cleanPrefix = prefix.trim().replaceAll(RegExp(r'^/+|/+$'), '');
    final safeFileName = fileName.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final objectKey =
        '${cleanPrefix.isEmpty ? '' : '$cleanPrefix/'}${now.millisecondsSinceEpoch}_$safeFileName';
    final encodedKey = objectKey.split('/').map(Uri.encodeComponent).join('/');
    final host = region == 'us-east-1' ? '$bucket.s3.amazonaws.com' : '$bucket.s3.$region.amazonaws.com';
    final url = 'https://$host/$encodedKey';
    final mimeType = lookupMimeType(fileName, headerBytes: bytes.take(16).toList()) ??
        'application/octet-stream';
    final payloadHash = sha256.convert(bytes).toString();
    final signedHeaders = 'content-type;host;x-amz-content-sha256;x-amz-date';
    final canonicalHeaders = [
      'content-type:$mimeType',
      'host:$host',
      'x-amz-content-sha256:$payloadHash',
      'x-amz-date:$amzDate',
    ].join('\n');

    final canonicalRequest = [
      'PUT',
      '/$encodedKey',
      '',
      '$canonicalHeaders\n',
      signedHeaders,
      payloadHash,
    ].join('\n');

    final credentialScope = '$dateStamp/$region/s3/aws4_request';
    final stringToSign = [
      'AWS4-HMAC-SHA256',
      amzDate,
      credentialScope,
      sha256.convert(utf8.encode(canonicalRequest)).toString(),
    ].join('\n');

    final signature = _calculateSignature(
      secretKey: secretKey,
      dateStamp: dateStamp,
      region: region,
      stringToSign: stringToSign,
    );

    final authorization =
        'AWS4-HMAC-SHA256 Credential=$accessKey/$credentialScope, SignedHeaders=$signedHeaders, Signature=$signature';

    final response = await http.put(
      Uri.parse(url),
      headers: {
        'Authorization': authorization,
        'Content-Type': mimeType,
        'Host': host,
        'x-amz-content-sha256': payloadHash,
        'x-amz-date': amzDate,
      },
      body: bytes,
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('S3 upload failed (${response.statusCode}): ${response.body}');
    }

    return UploadResult(
      objectKey: objectKey,
      url: url,
    );
  }

  static String _dateStamp(DateTime time) {
    final year = time.year.toString().padLeft(4, '0');
    final month = time.month.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    return '$year$month$day';
  }

  static String _amzDate(DateTime time) {
    final year = time.year.toString().padLeft(4, '0');
    final month = time.month.toString().padLeft(2, '0');
    final day = time.day.toString().padLeft(2, '0');
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    final second = time.second.toString().padLeft(2, '0');
    return '$year$month$day'
        'T$hour$minute$second'
        'Z';
  }

  static String _calculateSignature({
    required String secretKey,
    required String dateStamp,
    required String region,
    required String stringToSign,
  }) {
    final kDate = Hmac(sha256, utf8.encode('AWS4$secretKey')).convert(utf8.encode(dateStamp)).bytes;
    final kRegion = Hmac(sha256, kDate).convert(utf8.encode(region)).bytes;
    final kService = Hmac(sha256, kRegion).convert(utf8.encode('s3')).bytes;
    final kSigning = Hmac(sha256, kService).convert(utf8.encode('aws4_request')).bytes;
    return Hmac(sha256, kSigning).convert(utf8.encode(stringToSign)).toString();
  }
}