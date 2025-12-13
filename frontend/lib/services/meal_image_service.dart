import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class MealImageService {
  final SupabaseClient _supabase = Supabase.instance.client;

  // Backend URL - update this to match your backend
  static const String baseUrl = 'http://localhost:8000';

  /// Upload and analyze a meal image
  ///
  /// Returns a map containing:
  /// - success: bool
  /// - meal_log: Map with meal log data (id, meal, description, image_url, etc.)
  /// - analysis: Map with nutritional analysis (carbs, calories, etc.)
  /// - message: String (success/error message)
  Future<Map<String, dynamic>> analyzeMealImage(File imageFile) async {
    try {
      // Get access token
      final session = _supabase.auth.currentSession;
      if (session == null) {
        return {
          'success': false,
          'message': 'Not authenticated',
        };
      }

      // Create multipart request
      final uri = Uri.parse('$baseUrl/api/meals/analyze-image');
      final request = http.MultipartRequest('POST', uri);

      // Add authorization header
      request.headers['Authorization'] = 'Bearer ${session.accessToken}';

      // Determine MIME type based on file extension
      String mimeType = 'image/jpeg'; // Default
      final extension = imageFile.path.split('.').last.toLowerCase();
      if (extension == 'png') {
        mimeType = 'image/png';
      } else if (extension == 'heic') {
        mimeType = 'image/heic';
      } else if (extension == 'webp') {
        mimeType = 'image/webp';
      }

      // Add image file
      final multipartFile = await http.MultipartFile.fromPath(
        'file', // Field name must match backend expectation
        imageFile.path,
        contentType: MediaType.parse(mimeType),
      );
      request.files.add(multipartFile);

      // Send request
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      // Parse response
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return data;
      } else {
        // Handle error
        String errorMessage = 'Failed to analyze image';
        try {
          final errorData = jsonDecode(response.body);
          errorMessage = errorData['detail'] ?? errorMessage;
        } catch (e) {
          // If JSON parsing fails, use status code message
          errorMessage = 'Server error: ${response.statusCode}';
        }

        return {
          'success': false,
          'message': errorMessage,
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'Error uploading image: ${e.toString()}',
      };
    }
  }

  /// Get meal logs for the current user
  ///
  /// Parameters:
  /// - limit: Maximum number of logs to fetch (default: 50)
  /// - offset: Number of logs to skip for pagination (default: 0)
  Future<Map<String, dynamic>> getMealLogs({
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      // Get access token
      final session = _supabase.auth.currentSession;
      if (session == null) {
        return {
          'success': false,
          'message': 'Not authenticated',
          'meal_logs': [],
        };
      }

      // Make request
      final uri = Uri.parse('$baseUrl/api/meals/?limit=$limit&offset=$offset');
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Bearer ${session.accessToken}',
          'Content-Type': 'application/json',
        },
      );

      // Parse response
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {
          'success': false,
          'message': 'Failed to fetch meal logs',
          'meal_logs': [],
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'Error fetching meal logs: ${e.toString()}',
        'meal_logs': [],
      };
    }
  }

  /// Delete a meal log by ID
  Future<Map<String, dynamic>> deleteMealLog(String mealId) async {
    try {
      // Get access token
      final session = _supabase.auth.currentSession;
      if (session == null) {
        return {
          'success': false,
          'message': 'Not authenticated',
        };
      }

      // Make request
      final uri = Uri.parse('$baseUrl/api/meals/$mealId');
      final response = await http.delete(
        uri,
        headers: {
          'Authorization': 'Bearer ${session.accessToken}',
          'Content-Type': 'application/json',
        },
      );

      // Parse response
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {
          'success': false,
          'message': 'Failed to delete meal log',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'Error deleting meal log: ${e.toString()}',
      };
    }
  }
}
