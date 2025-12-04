class UserProfile {
  final String id;
  final String? firstName;
  final String? lastName;
  final String? sex;
  final String? ethnicity;
  final int? age;
  final String? activityLevel;
  final String? location;

  UserProfile({
    required this.id,
    this.firstName,
    this.lastName,
    this.sex,
    this.ethnicity,
    this.age,
    this.activityLevel,
    this.location,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      sex: json['sex'],
      ethnicity: json['ethnicity'],
      age: json['age'],
      activityLevel: json['activity_level'],
      location: json['location'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'first_name': firstName,
      'last_name': lastName,
      'sex': sex,
      'ethnicity': ethnicity,
      'age': age,
      'activity_level': activityLevel,
      'location': location,
    };
  }

  UserProfile copyWith({
    String? firstName,
    String? lastName,
    String? sex,
    String? ethnicity,
    int? age,
    String? activityLevel,
    String? location,
  }) {
    return UserProfile(
      id: id,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      sex: sex ?? this.sex,
      ethnicity: ethnicity ?? this.ethnicity,
      age: age ?? this.age,
      activityLevel: activityLevel ?? this.activityLevel,
      location: location ?? this.location,
    );
  }
}