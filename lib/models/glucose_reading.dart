class GlucoseReading {
  final String? id;
  final String userId;
  final double reading;
  final String? timing;
  final String? notes;
  final String? photoUrl;
  final DateTime createdAt;

  GlucoseReading({
    this.id,
    required this.userId,
    required this.reading,
    this.timing,
    this.notes,
    this.photoUrl,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();

  factory GlucoseReading.fromJson(Map<String, dynamic> json) {
    return GlucoseReading(
      id: json['id'],
      userId: json['user_id'],
      reading: (json['reading'] as num).toDouble(),
      timing: json['timing'],
      notes: json['notes'],
      photoUrl: json['photo_url'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'reading': reading,
      'timing': timing,
      'notes': notes,
      'photo_url': photoUrl,
    };
  }
}