import 'dart:async';
import 'dart:convert';

import 'package:flutter_client_sse/flutter_client_sse.dart';
import 'package:flutter_client_sse/constants/sse_request_type_enum.dart';

class ChatEvent {
  final String type; // 'tokens', 'status', 'done'
  final dynamic value;

  ChatEvent({required this.type, this.value});
}

class ChatStreamService {
  ChatStreamService(this.baseUrl);

  final String baseUrl; // e.g. http://localhost:8000

  Stream<ChatEvent> streamChat({
    required List<Map<String, String>> messages,
    String? accessToken,
  }) {
    final controller = StreamController<ChatEvent>();

    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    };
    if (accessToken != null) {
      headers['Authorization'] = 'Bearer $accessToken';
    }

    final bodyMap = <String, dynamic>{
      'messages': messages,
    };

    print('--SUBSCRIBING TO SSE---');
    print('URL: $baseUrl/chat_stream');
    print('Body: $bodyMap');

    try {
      final stream = SSEClient.subscribeToSSE(
        url: '$baseUrl/chat_stream',
        method: SSERequestType.POST,
        header: headers,
        body: bodyMap,
      );

      stream.listen(
        (event) {
          print('---SSE EVENT RECEIVED---');
          print('Event ID: ${event.id}');
          print('Event Type: ${event.event}');
          print('Event Data: ${event.data}');
          
          final data = event.data;
          if (data == null || data.isEmpty) {
            print('Empty data, skipping');
            return;
          }

          try {
            // SSE format: "data: {...}\n\n"
            String cleanData = data.trim();
            if (cleanData.startsWith('data: ')) {
              cleanData = cleanData.substring(6).trim();
            }

            print('Parsing clean data: $cleanData');
            final decoded = jsonDecode(cleanData) as Map<String, dynamic>;
            final type = decoded['type'] as String? ?? '';
            final value = decoded['value'];
            
            print('Decoded type: $type, value: $value');
            controller.add(ChatEvent(type: type, value: value));
            
            if (type == 'done') {
              print('---DONE EVENT, CLOSING STREAM---');
              controller.close();
            }
          } catch (e, stackTrace) {
            print('Error parsing SSE data: $e');
            print('Stack trace: $stackTrace');
            print('Raw data: $data');
          }
        },
        onError: (error, stackTrace) {
          print('---SSE STREAM ERROR---');
          print('Error: $error');
          print('Stack trace: $stackTrace');
          controller.addError(error, stackTrace);
          controller.close();
        },
        onDone: () {
          print('---SSE STREAM DONE (onDone callback)---');
          controller.close();
        },
        cancelOnError: false,
      );
    } catch (e, stackTrace) {
      print('---ERROR CREATING SSE CONNECTION---');
      print('Error: $e');
      print('Stack trace: $stackTrace');
      controller.addError(e, stackTrace);
      controller.close();
    }

    return controller.stream;
  }
}


