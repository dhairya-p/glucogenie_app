import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../providers/chat_provider.dart';

class AiChatbotScreen extends ConsumerStatefulWidget {
  const AiChatbotScreen({super.key});

  @override
  ConsumerState<AiChatbotScreen> createState() => _AiChatbotScreenState();
}

class _AiChatbotScreenState extends ConsumerState<AiChatbotScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    _messageController.clear();

    // Get Supabase access token
    final session = Supabase.instance.client.auth.currentSession;
    final accessToken = session?.accessToken;

    // Determine backend URL based on platform
    // For iOS simulator: localhost works
    // For Android emulator: use 10.0.2.2
    const baseUrl = 'http://localhost:8000';

    // Start streaming
    ref.read(chatControllerProvider.notifier).startStreaming(
          userMessage: text,
          baseUrl: baseUrl,
          accessToken: accessToken,
        );

    // Scroll to bottom after a short delay
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatControllerProvider);

    // Auto-scroll when new messages arrive
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      }
    });

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text('Chat with GlucoGenie'),
        centerTitle: true,
        elevation: 0,
      ),
      body: Column(
        children: [
          // Chat history
          Expanded(
            child: chatState.messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          size: 64,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Hi! I\'m your GlucoGenie assistant.\nAsk me anything about your glucose logs, meals, or activity.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: chatState.messages.length,
                    itemBuilder: (context, index) {
                      final message = chatState.messages[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _ChatBubble(
                          isUser: message.role == 'user',
                          message: message.content,
                        ),
                      );
                    },
                  ),
          ),
          // Status indicator
          if (chatState.isStreaming || chatState.status != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: Colors.grey[100],
              child: Row(
                children: [
                  if (chatState.isStreaming) ...[
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Theme.of(context).primaryColor,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'AI is thinking...',
                        style: TextStyle(
                          color: Colors.grey[700],
                          fontSize: 12,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                  if (chatState.status != null && !chatState.isStreaming)
                    Expanded(
                      child: Text(
                        chatState.status!.startsWith('error')
                            ? 'Error occurred'
                            : 'Status: ${chatState.status}',
                        style: TextStyle(
                          color: chatState.status!.startsWith('error')
                              ? Colors.red[700]
                              : Colors.grey[600],
                          fontSize: 12,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),
          // Input area
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            decoration: BoxDecoration(
              color: Colors.grey[50],
              border: Border(
                top: BorderSide(color: Colors.grey[300]!),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    enabled: !chatState.isStreaming,
                    decoration: InputDecoration(
                      hintText: chatState.isStreaming
                          ? 'AI is responding...'
                          : 'Type your question...',
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey[300]!),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey[300]!),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: const BorderSide(
                          color: Color(0xFF6366F1),
                          width: 2,
                        ),
                      ),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                FloatingActionButton.small(
                  onPressed: chatState.isStreaming ? null : _sendMessage,
                  backgroundColor: const Color(0xFF6366F1),
                  child: const Icon(Icons.send, color: Colors.white),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final bool isUser;
  final String message;

  const _ChatBubble({
    required this.isUser,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    final alignment =
        isUser ? MainAxisAlignment.end : MainAxisAlignment.start;
    final bubbleColor = isUser
        ? const Color(0xFF6366F1)
        : Colors.grey[200];
    final textColor = isUser ? Colors.white : Colors.black87;

    return Row(
      mainAxisAlignment: alignment,
      children: [
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 12,
            ),
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(16),
                topRight: const Radius.circular(16),
                bottomLeft:
                    isUser ? const Radius.circular(16) : const Radius.circular(4),
                bottomRight:
                    isUser ? const Radius.circular(4) : const Radius.circular(16),
              ),
            ),
            child: Text(
              message,
              style: TextStyle(color: textColor),
            ),
          ),
        ),
      ],
    );
  }
}
