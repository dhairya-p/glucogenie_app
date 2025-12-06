import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/database_service.dart';

class MealLogScreen extends StatefulWidget {
  const MealLogScreen({super.key});

  @override
  State<MealLogScreen> createState() => _MealLogScreenState();
}

class _MealLogScreenState extends State<MealLogScreen> {
  final _mealController = TextEditingController();
  final _descriptionController = TextEditingController();

  @override
  void dispose() {
    _mealController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _saveMeal() async {
    if (_mealController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a meal name')),
      );
      return;
    }

    final userId = context.read<AuthService>().currentUser?.id;
    if (userId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to log meals')),
      );
      return;
    }

    try {
      final success = await context.read<DatabaseService>().addMealLog(
        userId: userId,
        meal: _mealController.text.trim(),
        description: _descriptionController.text.trim().isEmpty 
            ? null 
            : _descriptionController.text.trim(),
      );

      if (!mounted) return;

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Meal logged successfully'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to log meal. Please check your connection and try again.'),
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
        title: const Text('Log Meal'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'What did you eat?',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 32),
            TextField(
              controller: _mealController,
              decoration: const InputDecoration(
                labelText: 'Meal Name *',
                hintText: 'e.g., Breakfast, Lunch, Chicken Rice',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.restaurant),
              ),
              textCapitalization: TextCapitalization.words,
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (Optional)',
                hintText: 'e.g., 1 cup rice, 2 pieces chicken, vegetables',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.description),
              ),
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: () {
                // TODO: Implement photo upload
              },
              icon: const Icon(Icons.camera_alt, size: 28),
              label: const Text(
                'Upload Photo',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 24),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 4,
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                // TODO: Implement voice mode
              },
              icon: const Icon(Icons.mic),
              label: const Text('Use voice mode'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple.withOpacity(0.1),
                foregroundColor: Colors.purple,
                padding: const EdgeInsets.all(16),
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _saveMeal,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Save Meal',
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

