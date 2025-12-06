import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/database_service.dart';

class ActivityLogScreen extends StatefulWidget {
  const ActivityLogScreen({Key? key}) : super(key: key);

  @override
  State<ActivityLogScreen> createState() => _ActivityLogScreenState();
}

class _ActivityLogScreenState extends State<ActivityLogScreen> {
  String? _selectedActivity;
  String _intensity = 'Medium';
  final _durationController = TextEditingController();
  final _notesController = TextEditingController();

  final List<String> _activityTypes = [
    'Walking',
    'Running',
    'Cycling',
    'Swimming',
    'Yoga',
    'Gym/Weights',
    'Dancing',
    'Sports',
    'Hiking',
    'Other',
  ];

  @override
  void dispose() {
    _durationController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _saveActivity() async {
    if (_selectedActivity == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an activity type')),
      );
      return;
    }

    if (_durationController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter duration')),
      );
      return;
    }

    final duration = int.tryParse(_durationController.text);
    if (duration == null || duration <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid duration in minutes')),
      );
      return;
    }

    final userId = context.read<AuthService>().currentUser?.id;
    if (userId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to log activity')),
      );
      return;
    }

    final success = await context.read<DatabaseService>().addActivityLog(
      userId: userId,
      activityType: _selectedActivity!,
      intensity: _intensity,
      durationMinutes: duration,
      notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
    );

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Activity logged successfully'),
          backgroundColor: Colors.green,
        ),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to log activity. Please check your connection and try again.'),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Log Activity'),
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
              'Activity',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedActivity,
              decoration: InputDecoration(
                labelText: 'Select Activity Type',
                prefixIcon: const Icon(Icons.directions_run),
                filled: true,
                fillColor: Colors.grey[100],
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
              items: _activityTypes.map((activity) {
                return DropdownMenuItem(
                  value: activity,
                  child: Text(activity),
                );
              }).toList(),
              onChanged: (value) {
                setState(() => _selectedActivity = value);
              },
            ),
            const SizedBox(height: 24),
            Text('Intensity', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: ['Low', 'Medium', 'High'].map((intensity) {
                return ChoiceChip(
                  label: Text(intensity),
                  selected: _intensity == intensity,
                  onSelected: (selected) {
                    if (selected) setState(() => _intensity = intensity);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
            Text('Duration (minutes)', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            TextField(
              controller: _durationController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                hintText: '30',
                filled: true,
                fillColor: Colors.grey[100],
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text('Notes (Optional)', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            TextField(
              controller: _notesController,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'How did you feel? Any observations...',
                filled: true,
                fillColor: Colors.grey[100],
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange[200]!),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.orange[700], size: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Regular physical activity helps manage blood glucose levels and overall health.',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.orange[900],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _saveActivity,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.all(18),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Save Activity',
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