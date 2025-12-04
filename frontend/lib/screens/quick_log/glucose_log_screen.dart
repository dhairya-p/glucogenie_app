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

    final userId = context.read<AuthService>().currentUser?.id;
    if (userId == null) return;

    final glucoseReading = GlucoseReading(
      userId: userId,
      reading: reading,
      timing: _timing,
    );

    final success = await context.read<DatabaseService>().addGlucoseReading(glucoseReading);

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reading saved successfully')),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to save reading')),
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
            const SizedBox(height: 24),
            
            const SizedBox(height: 32),
            OutlinedButton.icon(
              onPressed: () {
                // TODO: Implement photo upload
              },
              icon: const Icon(Icons.camera_alt),
              label: const Text('Upload Photo'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.all(16),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                // TODO: Implement voice mode
              },
              icon: const Icon(Icons.mic),
              label: const Text('Use voice mode'),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _saveReading,
              child: const Text('Save Reading'),
            ),
          ],
        ),
      ),
    );
  }
}
