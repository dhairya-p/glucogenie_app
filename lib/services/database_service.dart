import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/user_profile.dart';
import '../models/glucose_reading.dart';

class DatabaseService extends ChangeNotifier {
  final SupabaseClient _supabase = Supabase.instance.client;

  UserProfile? _userProfile;
  List<GlucoseReading> _glucoseReadings = [];

  UserProfile? get userProfile => _userProfile;
  List<GlucoseReading> get glucoseReadings => _glucoseReadings;

  // Create or update complete profile
  Future<bool> createOrUpdateCompleteProfile({
    required String userId,
    required String firstName,
    required String lastName,
    required String sex,
    required int age,
    String? ethnicity,
    String? location,
    String? activityLevel,
  }) async {
    try {      
      // Wait for trigger to create the profile row
      await Future.delayed(const Duration(seconds: 2));
      
      // Build profile data
      final Map<String, dynamic> profileData = {
        'first_name': firstName,
        'last_name': lastName,
        'sex': sex,
        'age': age,
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (ethnicity != null && ethnicity.isNotEmpty) {
        profileData['ethnicity'] = ethnicity;
      }
      if (location != null && location.isNotEmpty) {
        profileData['location'] = location;
      }
      if (activityLevel != null && activityLevel.isNotEmpty) {
        profileData['activity_level'] = activityLevel;
      }
      await _supabase
          .from('profiles')
          .update(profileData)
          .eq('id', userId);
      
      await Future.delayed(const Duration(milliseconds: 500));
      
      return true;
    } catch (e, stackTrace) {
      return false;
    }
  }

  // Fetch user profile - can accept userId or use currentUser
  Future<void> fetchUserProfile({String? userId}) async {
    try {
      final id = userId ?? _supabase.auth.currentUser?.id;
      if (id == null) {
        return;
      }
      
      final response = await _supabase
          .from('profiles')
          .select()
          .eq('id', id)
          .single();

      _userProfile = UserProfile.fromJson(response);
      notifyListeners();
    } catch(e) {
      return;
    }
  }

  // Update user profile
  Future<bool> updateUserProfile(UserProfile profile) async {
    try {
      final profileData = profile.toJson();
      
      await _supabase
          .from('profiles')
          .update(profileData)
          .eq('id', profile.id);
      
      _userProfile = profile;
      notifyListeners();
      return true;
    } catch (e) {
      return false;
    }
  }

  // Add condition - FIXED to accept userId parameter
  Future<bool> addCondition(String conditionName, {String? userId}) async {
    try {
      final id = userId ?? _supabase.auth.currentUser?.id;
      if (id == null) {
        return false;
      }
      
      // Check if condition already exists
      final existing = await _supabase
          .from('conditions')
          .select()
          .eq('user_id', id)
          .eq('condition_name', conditionName);

      if (existing.isNotEmpty) {
        return true;
      }

      await _supabase.from('conditions').insert({
        'user_id': id,
        'condition_name': conditionName,
      });
      
      return true;
    } catch (e) {
      return false;
    }
  }

  // Add medication - FIXED to accept userId parameter
  Future<bool> addMedication(String medicationName, {String? userId}) async {
    try {
      final id = userId ?? _supabase.auth.currentUser?.id;
      if (id == null) {
        return false;
      }
      
      // Check if medication already exists
      final existing = await _supabase
          .from('medications')
          .select()
          .eq('user_id', id)
          .eq('medication_name', medicationName);

      if (existing.isNotEmpty) {
        return true;
      }

      await _supabase.from('medications').insert({
        'user_id': id,
        'medication_name': medicationName,
      });
      
      return true;
    } catch (e) {
      return false;
    }
  }

  // Fetch glucose readings
  Future<void> fetchGlucoseReadings() async {
    try {
      final userId = _supabase.auth.currentUser?.id;
      if (userId == null) return;

      final response = await _supabase
          .from('glucose_readings')
          .select()
          .eq('user_id', userId)
          .order('created_at', ascending: false)
          .limit(30);

      _glucoseReadings = (response as List)
          .map((json) => GlucoseReading.fromJson(json))
          .toList();
      notifyListeners();
    } catch(e) {
      return;
    }
  }

  // Add glucose reading
  Future<bool> addGlucoseReading(GlucoseReading reading) async {
    try {
      await _supabase.from('glucose_readings').insert(reading.toJson());
      await fetchGlucoseReadings();
      return true;
    } catch (e) {
      return false;
    }
  }

  // Add weight log
  Future<bool> addWeightLog({
    required String userId,
    required double weight,
    required String unit,
    String? notes,
  }) async {
    try {
      await _supabase.from('weight_logs').insert({
        'user_id': userId,
        'weight': weight,
        'unit': unit,
        'notes': notes,
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  // Add medication log
  Future<bool> addMedicationLog({
    required String userId,
    required String medicationName,
    required String quantity,
    String? notes,
  }) async {
    try {
      await _supabase.from('medication_logs').insert({
        'user_id': userId,
        'medication_name': medicationName,
        'quantity': quantity,
        'notes': notes,
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  // Add activity log
  Future<bool> addActivityLog({
    required String userId,
    required String activityType,
    required String intensity,
    required int durationMinutes,
    String? notes,
  }) async {
    try {
      await _supabase.from('activity_logs').insert({
        'user_id': userId,
        'activity_type': activityType,
        'intensity': intensity,
        'duration_minutes': durationMinutes,
        'notes': notes,
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  // Get conditions for user - FIXED to accept userId parameter
  Future<List<String>> getConditions({String? userId}) async {
    try {
      final id = userId ?? _supabase.auth.currentUser?.id;
      if (id == null) {
        return [];
      }

      final response = await _supabase
          .from('conditions')
          .select('condition_name')
          .eq('user_id', id);
      
      final conditions = (response as List).map((e) => e['condition_name'] as String).toList();
      return conditions;
    } catch (e) {
      return [];
    }
  }

  // Get medications for user - FIXED to accept userId parameter
  Future<List<String>> getMedications({String? userId}) async {
    try {
      final id = userId ?? _supabase.auth.currentUser?.id;
      if (id == null) {
        return [];
      }

      final response = await _supabase
          .from('medications')
          .select('medication_name')
          .eq('user_id', id);
      
      final medications = (response as List).map((e) => e['medication_name'] as String).toList();
      return medications;
    } catch (e) {
      return [];
    }
  }

  // Delete condition
  Future<bool> deleteCondition(String conditionName) async {
    try {
      final userId = _supabase.auth.currentUser?.id;
      if (userId == null) return false;

      await _supabase
          .from('conditions')
          .delete()
          .eq('user_id', userId)
          .eq('condition_name', conditionName);
      
      return true;
    } catch (e) {
      return false;
    }
  }

  // Delete medication
  Future<bool> deleteMedication(String medicationName) async {
    try {
      final userId = _supabase.auth.currentUser?.id;
      if (userId == null) return false;

      await _supabase
          .from('medications')
          .delete()
          .eq('user_id', userId)
          .eq('medication_name', medicationName);
      
      return true;
    } catch (e) {
      return false;
    }
  }
}