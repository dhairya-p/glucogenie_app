import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/chat_stream_service.dart';

class ChatMessage {
  ChatMessage({required this.role, required this.content});

  final String role; // 'user' | 'assistant' | 'system'
  final String content;

  Map<String, String> toJson() => {
        'role': role,
        'content': content,
      };
}

class ChatState {
  const ChatState({
    this.messages = const [],
    this.isStreaming = false,
    this.status,
    this.statusDetails = const {},
  });

  final List<ChatMessage> messages;
  final bool isStreaming;
  final String? status;
  final Map<String, String> statusDetails;

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isStreaming,
    String? status,
    Map<String, String>? statusDetails,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isStreaming: isStreaming ?? this.isStreaming,
      status: status ?? this.status,
      statusDetails: statusDetails ?? this.statusDetails,
    );
  }
}

class ChatController extends StateNotifier<ChatState> {
  ChatController(this._service) : super(const ChatState());

  final ChatStreamService _service;
  StreamSubscription<ChatEvent>? _subscription;

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  void addUserMessage(String content) {
    final updated = List<ChatMessage>.from(state.messages)
      ..add(ChatMessage(role: 'user', content: content));
    state = state.copyWith(messages: updated);
  }

  Future<void> startStreaming({
    required String userMessage,
    required String baseUrl,
    String? accessToken,
  }) async {
    // Append user message to the conversation
    final history = List<ChatMessage>.from(state.messages)
      ..add(ChatMessage(role: 'user', content: userMessage));
    state = state.copyWith(
      messages: history,
      isStreaming: true,
      status: null,
      statusDetails: const {},
    );

    // Create a new service bound to the current backend URL
    final service = ChatStreamService(baseUrl);

    // Cancel any previous stream
    await _subscription?.cancel();

    // Start listening to the SSE stream
    _subscription = service
        .streamChat(
          messages: history.map((m) => m.toJson()).toList(),
          accessToken: accessToken,
        )
        .listen(
      (event) {
        
        if (event.type == 'tokens') {
          final token = (event.value ?? '').toString();
          if (token.isEmpty) {
            return;
          }

          // Append or extend the latest assistant message
          final messages = List<ChatMessage>.from(state.messages);
          if (messages.isNotEmpty && messages.last.role == 'assistant') {
            final last = messages.removeLast();
            messages.add(
              ChatMessage(
                role: 'assistant',
                content: last.content + token,
              ),
            );
          } else {
            messages.add(ChatMessage(role: 'assistant', content: token));
          }
          state = state.copyWith(messages: messages);
          print('Updated messages count: ${messages.length}');
        } else if (event.type == 'status') {
          final value = event.value;
          if (value is Map<String, dynamic>) {
            final stage = value['stage']?.toString() ?? '';
            final details = Map<String, String>.from(state.statusDetails);

            if (stage == 'routing') {
              details['Agent'] = value['agent']?.toString() ?? 'unmatched';
            } else if (stage == 'rag') {
              final sources = (value['sources'] as List?)?.map((s) => s.toString()).toList() ?? [];
              if (sources.isNotEmpty) {
                details['Sources'] = sources.join(', ');
              }
              final ragChars = value['rag_chars']?.toString();
              if (ragChars != null) {
                details['RAG chars'] = ragChars;
              }
            }

            state = state.copyWith(status: null, statusDetails: details);
          }
        } else if (event.type == 'done') {
          print('---DONE EVENT RECEIVED---');
          // Clear status when done successfully
          state = state.copyWith(isStreaming: false, status: null);
        } else if (event.type == 'error') {
          print('---ERROR EVENT RECEIVED---');
          state = state.copyWith(
            isStreaming: false,
            status: 'error: ${event.value}',
          );
        }
      },
      onError: (error, stackTrace) {
        print('---PROVIDER STREAM ERROR---');
        print('Error: $error');
        print('Stack trace: $stackTrace');
        state = state.copyWith(
          isStreaming: false,
          status: 'error: $error',
        );
      },
      onDone: () {
        print('---PROVIDER STREAM DONE---');
        // Clear status when stream completes successfully
        state = state.copyWith(isStreaming: false, status: null);
      },
    );
  }
}

final chatControllerProvider =
    StateNotifierProvider<ChatController, ChatState>((ref) {
  // Backend URL - adjust for your environment:
  // - iOS Simulator: http://localhost:8000
  // - Android Emulator: http://10.0.2.2:8000
  // - Physical device: http://<your-local-ip>:8000
  const baseUrl = 'http://localhost:8000';
  final service = ChatStreamService(baseUrl);
  return ChatController(service);
});


