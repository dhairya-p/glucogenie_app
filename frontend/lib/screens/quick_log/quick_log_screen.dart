import 'package:flutter/material.dart';
import 'glucose_log_screen.dart';
import 'weight_log_screen.dart';
import 'medication_log_screen.dart';
import 'activity_log_screen.dart';

class QuickLogScreen extends StatelessWidget {
  const QuickLogScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Quick Log'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _buildLogCard(
            context,
            icon: Icons.water_drop,
            title: 'Blood Glucose Level & Meals',
            color: Colors.red,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const GlucoseLogScreen()),
              );
            },
          ),
          const SizedBox(height: 16),
          _buildLogCard(
            context,
            icon: Icons.monitor_weight,
            title: 'Weight',
            color: Colors.blue,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const WeightLogScreen()),
              );
            },
          ),
          const SizedBox(height: 16),
          _buildLogCard(
            context,
            icon: Icons.medication,
            title: 'Medication',
            color: Colors.green,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MedicationLogScreen()),
              );
            },
          ),
          const SizedBox(height: 16),
          _buildLogCard(
            context,
            icon: Icons.directions_run,
            title: 'Activity',
            color: Colors.orange,
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ActivityLogScreen()),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildLogCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey[200]!),
          boxShadow: [
            BoxShadow(
              color: Colors.grey.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 28),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
          ],
        ),
      ),
    );
  }
}