import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../services/database_service.dart';
import '../ai_chatbot_screen.dart';

class DashboardTab extends StatefulWidget {
  const DashboardTab({Key? key}) : super(key: key);

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DatabaseService>().fetchInsights();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Consumer<DatabaseService>(
                  builder: (context, dbService, _) {
                    final profile = dbService.userProfile;
                    final firstName = profile?.firstName ?? 'there';

                    return Text(
                      'Hello, $firstName!',
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    );
                  },
                ),
                IconButton(
                  icon: const Icon(Icons.chat_bubble_outline),
                  color: const Color(0xFF6366F1),
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const AiChatbotScreen(),
                      ),
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Your blood glucose level for today',
              style: TextStyle(color: Colors.grey[600]),
            ),
            const SizedBox(height: 24),
            Consumer<DatabaseService>(
              builder: (context, dbService, _) {
                final readings = dbService.glucoseReadings;
                final latestReading = readings.isNotEmpty ? readings.first : null;
                
                return Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${latestReading?.reading.toInt() ?? 0}',
                                style: TextStyle(
                                  fontSize: 48,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              Text(
                                'mg/dL',
                                style: TextStyle(
                                  fontSize: 18,
                                  color: Colors.white70,
                                ),
                              ),
                            ],
                          ),
                          Container(
                            height: 60,
                            width: 100,
                            decoration: BoxDecoration(
                              color: Colors.white24,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Center(
                              child: Icon(Icons.show_chart, 
                                  color: Colors.white, size: 32),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white24,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.info_outline, 
                                color: Colors.white, size: 16),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Target range: 70-130 mg/dL before meals',
                                style: TextStyle(color: Colors.white, fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(height: 24),
            Text(
              "Today's Insights (AI-generated)",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Consumer<DatabaseService>(
              builder: (context, dbService, _) {
                final insights = dbService.insights;
                
                if (insights.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.grey[50],
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.grey[200]!),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.grey[600]),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Insufficient data for personalized insights. Keep logging your glucose, meals, and activities!',
                            style: TextStyle(color: Colors.grey[600]),
                          ),
                        ),
                      ],
                    ),
                  );
                }
                
                return Column(
                  children: [
                    for (var insight in insights)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _buildInsightCard(
                          icon: _getInsightIcon(insight['title']?.toString() ?? ''),
                          iconColor: _getInsightColor(insight['title']?.toString() ?? ''),
                          title: insight['title']?.toString() ?? 'Insight',
                          subtitle: insight['detail']?.toString() ?? '',
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInsightCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    String? description,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(color: Colors.grey[700]),
                ),
                if (description != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(color: Colors.grey[600], fontSize: 13),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _getInsightIcon(String title) {
    final titleLower = title.toLowerCase();
    if (titleLower.contains('risk') || titleLower.contains('alert')) {
      return Icons.warning;
    } else if (titleLower.contains('pattern') || titleLower.contains('circadian')) {
      return Icons.trending_up;
    } else if (titleLower.contains('best') || titleLower.contains('optimal')) {
      return Icons.star;
    } else if (titleLower.contains('consistency')) {
      return Icons.schedule;
    } else if (titleLower.contains('personalized')) {
      return Icons.person;
    }
    return Icons.lightbulb;
  }

  Color _getInsightColor(String title) {
    final titleLower = title.toLowerCase();
    if (titleLower.contains('risk') || titleLower.contains('alert')) {
      return Colors.red;
    } else if (titleLower.contains('pattern') || titleLower.contains('circadian')) {
      return Colors.blue;
    } else if (titleLower.contains('best') || titleLower.contains('optimal')) {
      return Colors.orange;
    } else if (titleLower.contains('consistency')) {
      return Colors.purple;
    } else if (titleLower.contains('personalized')) {
      return Colors.green;
    }
    return Colors.orange;
  }
}