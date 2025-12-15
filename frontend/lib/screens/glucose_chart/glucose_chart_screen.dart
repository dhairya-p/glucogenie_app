import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../services/database_service.dart';

class GlucoseChartScreen extends StatefulWidget {
  const GlucoseChartScreen({Key? key}) : super(key: key);

  @override
  State<GlucoseChartScreen> createState() => _GlucoseChartScreenState();
}

class _GlucoseChartScreenState extends State<GlucoseChartScreen> {
  String _selectedRange = '7d';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Glucose Trends'),
        backgroundColor: const Color(0xFF6366F1),
        foregroundColor: Colors.white,
      ),
      body: Consumer<DatabaseService>(
        builder: (context, dbService, _) {
          final readings = dbService.glucoseReadings;
          final filteredReadings = _filterReadingsByRange(readings);

          return Column(
            children: [
              // Time range selector
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.grey.withOpacity(0.1),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildRangeButton('7d', '7 Days'),
                    _buildRangeButton('30d', '30 Days'),
                    _buildRangeButton('1y', '1 Year'),
                    _buildRangeButton('max', 'All Time'),
                  ],
                ),
              ),

              // Chart section
              Expanded(
                child: filteredReadings.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.insert_chart_outlined,
                              size: 64,
                              color: Colors.grey[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'No glucose data available',
                              style: TextStyle(
                                fontSize: 18,
                                color: Colors.grey[600],
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Start logging your glucose readings to see trends',
                              style: TextStyle(
                                fontSize: 14,
                                color: Colors.grey[500],
                              ),
                            ),
                          ],
                        ),
                      )
                    : SingleChildScrollView(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Stats summary
                            _buildStatsSection(filteredReadings),
                            const SizedBox(height: 24),

                            // Chart
                            Text(
                              'Glucose Levels Over Time',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 16),
                            Container(
                              height: 300,
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: Colors.grey[200]!),
                              ),
                              child: LineChart(
                                _buildChartData(filteredReadings),
                              ),
                            ),

                            const SizedBox(height: 24),

                            // Reading list
                            Text(
                              'Recent Readings',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            ...filteredReadings.reversed.take(10).map((reading) {
                              return _buildReadingListItem(reading);
                            }).toList(),
                          ],
                        ),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildRangeButton(String value, String label) {
    final isSelected = _selectedRange == value;
    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedRange = value;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF6366F1) : Colors.grey[100],
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.grey[700],
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            fontSize: 14,
          ),
        ),
      ),
    );
  }

  Widget _buildStatsSection(List<dynamic> readings) {
    if (readings.isEmpty) return const SizedBox.shrink();

    final glucoseValues = readings.map((r) => r.reading as double).toList();
    final avg = glucoseValues.reduce((a, b) => a + b) / glucoseValues.length;
    final max = glucoseValues.reduce((a, b) => a > b ? a : b);
    final min = glucoseValues.reduce((a, b) => a < b ? a : b);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem('Average', avg.toInt(), 'mg/dL'),
          _buildStatItem('Highest', max.toInt(), 'mg/dL'),
          _buildStatItem('Lowest', min.toInt(), 'mg/dL'),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, int value, String unit) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white70,
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value.toString(),
          style: TextStyle(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          unit,
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
          ),
        ),
      ],
    );
  }

  Widget _buildReadingListItem(dynamic reading) {
    final timestamp = reading.createdAt;
    final formattedDate = DateFormat('MMM dd, yyyy').format(timestamp);
    final formattedTime = DateFormat('hh:mm a').format(timestamp);
    final glucoseValue = reading.reading.toInt();

    // Determine status color
    Color statusColor;
    String status;
    if (glucoseValue < 70) {
      statusColor = Colors.red;
      status = 'Low';
    } else if (glucoseValue > 180) {
      statusColor = Colors.orange;
      status = 'High';
    } else {
      statusColor = Colors.green;
      status = 'Normal';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 40,
            decoration: BoxDecoration(
              color: statusColor,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  formattedDate,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                Text(
                  formattedTime,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$glucoseValue',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: statusColor,
                ),
              ),
              Text(
                'mg/dL',
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              status,
              style: TextStyle(
                color: statusColor,
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  LineChartData _buildChartData(List<dynamic> readings) {
    final spots = _getChartSpots(readings);

    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: Colors.grey[300]!,
            strokeWidth: 1,
          );
        },
      ),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            getTitlesWidget: (value, meta) {
              return Text(
                value.toInt().toString(),
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              );
            },
          ),
        ),
        rightTitles: AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        topTitles: AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            getTitlesWidget: (value, meta) {
              if (readings.isEmpty || value.toInt() >= readings.length) {
                return const Text('');
              }
              final reading = readings[value.toInt()];
              final timestamp = reading.createdAt;
              return Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: Text(
                  DateFormat('MM/dd').format(timestamp),
                  style: TextStyle(fontSize: 10, color: Colors.grey[600]),
                ),
              );
            },
          ),
        ),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border(
          left: BorderSide(color: Colors.grey[300]!),
          bottom: BorderSide(color: Colors.grey[300]!),
        ),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: spots,
          isCurved: true,
          color: const Color(0xFF6366F1),
          barWidth: 3,
          dotData: FlDotData(
            show: true,
            getDotPainter: (spot, percent, barData, index) {
              return FlDotCirclePainter(
                radius: 4,
                color: Colors.white,
                strokeWidth: 2,
                strokeColor: const Color(0xFF6366F1),
              );
            },
          ),
          belowBarData: BarAreaData(
            show: true,
            color: const Color(0xFF6366F1).withOpacity(0.1),
          ),
        ),
      ],
      minY: 0,
      maxY: 300,
      lineTouchData: LineTouchData(
        touchTooltipData: LineTouchTooltipData(
          getTooltipItems: (touchedSpots) {
            return touchedSpots.map((spot) {
              final reading = readings[spot.x.toInt()];
              final timestamp = reading.createdAt;
              final formattedDate = DateFormat('MMM dd, hh:mm a').format(timestamp);
              return LineTooltipItem(
                '${spot.y.toInt()} mg/dL\n$formattedDate',
                const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              );
            }).toList();
          },
        ),
      ),
    );
  }

  List<FlSpot> _getChartSpots(List<dynamic> readings) {
    if (readings.isEmpty) return [];

    // Create spots with index as x and reading as y
    return readings.asMap().entries.map((entry) {
      return FlSpot(entry.key.toDouble(), entry.value.reading.toDouble());
    }).toList();
  }

  List<dynamic> _filterReadingsByRange(List<dynamic> readings) {
    if (readings.isEmpty) return [];

    List<dynamic> filtered;
    final now = DateTime.now();
    DateTime cutoffDate;

    switch (_selectedRange) {
      case '7d':
        cutoffDate = now.subtract(const Duration(days: 7));
        break;
      case '30d':
        cutoffDate = now.subtract(const Duration(days: 30));
        break;
      case '1y':
        cutoffDate = now.subtract(const Duration(days: 365));
        break;
      case 'max':
        // For max, use all readings but still need to sort them
        filtered = List.from(readings);
        filtered.sort((a, b) => a.createdAt.compareTo(b.createdAt));
        return filtered;
      default:
        cutoffDate = now.subtract(const Duration(days: 7));
    }

    filtered = readings.where((r) {
      return r.createdAt.isAfter(cutoffDate);
    }).toList();

    // Sort by createdAt (oldest first for chart, chronologically left to right)
    filtered.sort((a, b) {
      return a.createdAt.compareTo(b.createdAt);
    });

    return filtered;
  }
}
