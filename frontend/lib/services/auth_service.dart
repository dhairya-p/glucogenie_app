import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AuthService extends ChangeNotifier {
  final SupabaseClient _supabase = Supabase.instance.client;

  User? get currentUser => _supabase.auth.currentUser;
  bool get isAuthenticated => currentUser != null;

  // Sign up - ONLY creates auth user, doesn't touch profiles
  Future<Map<String, dynamic>> signUp({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    try {
      debugPrint('Starting signup for email: $email');
      
      final response = await _supabase.auth.signUp(
        email: email,
        password: password,
      );

      if (response.user != null) {
        debugPrint('User created successfully: ${response.user!.id}');
        
        // Return user data to be saved by calling code
        notifyListeners();
        return {
          'success': true, 
          'message': 'Account created successfully',
          'userId': response.user!.id,
          'firstName': firstName,
          'lastName': lastName,
        };
      }

      debugPrint('Signup failed: No user returned');
      return {'success': false, 'message': 'Failed to create account'};
    } on AuthException catch (e) {
      debugPrint('Auth exception during signup: ${e.message}');
      return {'success': false, 'message': e.message};
    } catch (e) {
      debugPrint('Unexpected error during signup: $e');
      return {'success': false, 'message': 'An error occurred: $e'};
    }
  }

  // Sign in
  Future<Map<String, dynamic>> signIn({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _supabase.auth.signInWithPassword(
        email: email,
        password: password,
      );

      if (response.user != null) {
        notifyListeners();
        return {'success': true, 'message': 'Signed in successfully'};
      }

      return {'success': false, 'message': 'Failed to sign in'};
    } on AuthException catch (e) {
      return {'success': false, 'message': e.message};
    } catch (e) {
      return {'success': false, 'message': 'An error occurred'};
    }
  }

  // Sign out
  Future<void> signOut() async {
    await _supabase.auth.signOut();
    notifyListeners();
  }

  // Reset password
  Future<Map<String, dynamic>> resetPassword(String email) async {
    try {
      await _supabase.auth.resetPasswordForEmail(email);
      return {'success': true, 'message': 'Password reset email sent'};
    } on AuthException catch (e) {
      return {'success': false, 'message': e.message};
    } catch (e) {
      return {'success': false, 'message': 'An error occurred'};
    }
  }

  // Update password (for logged-in users)
  Future<Map<String, dynamic>> updatePassword(String newPassword) async {
    try {
      await _supabase.auth.updateUser(
        UserAttributes(password: newPassword),
      );
      return {'success': true, 'message': 'Password updated successfully'};
    } on AuthException catch (e) {
      return {'success': false, 'message': e.message};
    } catch (e) {
      return {'success': false, 'message': 'An error occurred'};
    }
  }
}