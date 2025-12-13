import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/glucose_reading.dart';
import '../../services/auth_service.dart';
import '../../services/database_service.dart';

class GlucoseLogScreen extends StatefulWidget {
  const GlucoseLogScreen({super.key});

  @override
  State<GlucoseLogScreen> createState() => _GlucoseLogScreenState();
}

class _GlucoseLogScreenState extends State<GlucoseLogScreen> {
  final _readingController = TextEditingController();
  String _timing = 'Just woke up';

  @override
  void dispose() {
    _readingController.dispose();
    super.dispose();
  }

  Future<void> _saveReading() async {
    if (_readingController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a glucose reading')),
      );
      return;
    }

    final reading = double.tryParse(_readingController.text);
    if (reading == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid number')),
      );
      return;
    }

    // Validate reading range (typical glucose range: 20-600 mg/dL)
    if (reading < 20 || reading > 600) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a glucose reading between 20-600 mg/dL'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    final userId = context.read<AuthService>().currentUser?.id;
    if (userId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to log glucose readings')),
      );
      return;
    }

    try {
      final glucoseReading = GlucoseReading(
        userId: userId,
        reading: reading,
        timing: _timing,
      );

      final success = await context.read<DatabaseService>().addGlucoseReading(glucoseReading);

      if (!mounted) return;

      if (success) {
        // Refresh insights to update dashboard
        context.read<DatabaseService>().fetchInsights();

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Reading saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to save reading. Please check your connection and try again.'),
            backgroundColor: Colors.red,
            duration: Duration(seconds: 4),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: ${e.toString()}'),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Blood Glucose'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Blood Glucose Reading',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: _readingController,
                    keyboardType: TextInputType.number,
                    style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text(
                    'mg/dL',
                    style: TextStyle(fontSize: 18, color: Colors.grey),
                  ),
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 24),
            Text('When?', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                'Just woke up',
                'Before meal',
                'After meal',
                'Bedtime'
              ].map((timing) {
                return ChoiceChip(
                  label: Text(timing),
                  selected: _timing == timing,
                  onSelected: (selected) {
                    if (selected) setState(() => _timing = timing);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _saveReading,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Save Reading',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
