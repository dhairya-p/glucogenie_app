import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/chat_provider.dart';

class AiChatbotScreen extends ConsumerStatefulWidget {
  const AiChatbotScreen({super.key});

  @override
  ConsumerState<AiChatbotScreen> createState() => _AiChatbotScreenState();
}

class _AiChatbotScreenState extends ConsumerState<AiChatbotScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _messageFocusNode = FocusNode();

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _messageFocusNode.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    // Request focus when screen is first shown
    // Use a small delay to ensure the widget tree is fully built
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 100), () {
        if (mounted) {
          _messageFocusNode.requestFocus();
        }
      });
    });
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

    // Keep focus on the text field and scroll to bottom after a short delay
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _messageFocusNode.requestFocus();
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
          // Status indicator - show agent + sources during streaming, errors always
          if (chatState.isStreaming ||
              (chatState.status != null && chatState.status!.startsWith('error')) ||
              chatState.statusDetails.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: chatState.status != null && chatState.status!.startsWith('error')
                  ? Colors.red[50]
                  : Colors.grey[100],
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
                      child: _StatusDetails(
                        statusDetails: chatState.statusDetails,
                      ),
                    ),
                  ],
                  if (chatState.status != null && 
                      chatState.status!.startsWith('error') && 
                      !chatState.isStreaming)
                    Expanded(
                      child: Row(
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 16,
                            color: Colors.red[700],
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Error: ${chatState.status!.replaceFirst('error: ', '')}',
                              style: TextStyle(
                                color: Colors.red[700],
                                fontSize: 12,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
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
                    focusNode: _messageFocusNode,
                    autofocus: true,
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
            child: isUser
                ? Text(
                    message,
                    style: TextStyle(color: textColor),
                  )
                : MarkdownBody(
                    data: message,
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      // Base text styling
                      p: TextStyle(
                        color: textColor,
                        fontSize: 15,
                        height: 1.5,
                      ),
                      // Headers
                      h1: TextStyle(
                        color: textColor,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      h2: TextStyle(
                        color: textColor,
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      h3: TextStyle(
                        color: textColor,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      h4: TextStyle(
                        color: textColor,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      h5: TextStyle(
                        color: textColor,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      h6: TextStyle(
                        color: textColor,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                      // Bold text
                      strong: TextStyle(
                        color: textColor,
                        fontWeight: FontWeight.bold,
                      ),
                      // Italic text
                      em: TextStyle(
                        color: textColor,
                        fontStyle: FontStyle.italic,
                      ),
                      // Code blocks
                      code: TextStyle(
                        color: textColor,
                        backgroundColor: isUser
                            ? Colors.white.withOpacity(0.2)
                            : Colors.grey[300],
                        fontFamily: 'monospace',
                        fontSize: 14,
                      ),
                      codeblockDecoration: BoxDecoration(
                        color: isUser
                            ? Colors.white.withOpacity(0.15)
                            : Colors.grey[300],
                        borderRadius: BorderRadius.circular(6),
                      ),
                      codeblockPadding: const EdgeInsets.all(12),
                      // Blockquotes
                      blockquote: TextStyle(
                        color: textColor.withOpacity(0.8),
                        fontStyle: FontStyle.italic,
                      ),
                      blockquoteDecoration: BoxDecoration(
                        color: isUser
                            ? Colors.white.withOpacity(0.1)
                            : Colors.grey[300],
                        border: Border(
                          left: BorderSide(
                            color: textColor.withOpacity(0.5),
                            width: 4,
                          ),
                        ),
                      ),
                      blockquotePadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      // Lists
                      listBullet: TextStyle(color: textColor),
                      // Links
                      a: TextStyle(
                        color: isUser
                            ? Colors.white
                            : const Color(0xFF6366F1),
                        decoration: TextDecoration.underline,
                        decorationColor: isUser
                            ? Colors.white
                            : const Color(0xFF6366F1),
                      ),
                      // Horizontal rules
                      horizontalRuleDecoration: BoxDecoration(
                        border: Border(
                          top: BorderSide(
                            color: textColor.withOpacity(0.3),
                            width: 1,
                          ),
                        ),
                      ),
                      // Table styling
                      tableHead: TextStyle(
                        color: textColor,
                        fontWeight: FontWeight.bold,
                      ),
                      tableBody: TextStyle(color: textColor),
                      tableBorder: TableBorder.all(
                        color: textColor.withOpacity(0.3),
                        width: 1,
                      ),
                      // Spacing
                      blockSpacing: 8.0,
                      listIndent: 24.0,
                      textScaleFactor: 1.0,
                    ),
                    onTapLink: (text, href, title) async {
                      if (href != null) {
                        final uri = Uri.parse(href);
                        if (await canLaunchUrl(uri)) {
                          await launchUrl(uri, mode: LaunchMode.externalApplication);
                        }
                      }
                    },
                  ),
          ),
        ),
      ],
    );
  }
}

class _StatusDetails extends StatelessWidget {
  final Map<String, String> statusDetails;

  const _StatusDetails({required this.statusDetails});

  @override
  Widget build(BuildContext context) {
    if (statusDetails.isEmpty) {
      return Text(
        'Processing...',
        style: TextStyle(
          color: Colors.grey[700],
          fontSize: 12,
        ),
        overflow: TextOverflow.ellipsis,
      );
    }

    final entries = statusDetails.entries.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final entry in entries)
          Text(
            '${entry.key}: ${entry.value}',
            style: TextStyle(
              color: Colors.grey[700],
              fontSize: 12,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
      ],
    );
  }
}
