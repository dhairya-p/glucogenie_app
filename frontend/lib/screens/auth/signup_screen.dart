import 'package:diabetes_fyp/screens/auth/login_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/database_service.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({Key? key}) : super(key: key);

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _locationController = TextEditingController();
  
  String _sex = 'Male';
  String? _ethnicity;
  int _age = 50;
  int? _height;
  String? _activityLevel;
  
  List<String> _selectedConditions = [];
  List<String> _selectedMedications = [];
  
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  final List<String> _ethnicityOptions = [
    'Chinese',
    'Indian',
    'Malay',
    'Eurasian',
    'Asian',
    'Other Asian',
    'Black or African American',
    'Hispanic or Latino',
    'White or Caucasian',
    'Native American or Alaska Native',
    'Native Hawaiian or Pacific Islander',
    'Middle Eastern or North African',
    'Mixed or Multiracial',
    'Other',
    'Prefer not to say',
  ];

  final List<String> _activityLevelOptions = [
    'Sedentary (little or no exercise)',
    'Lightly Active (light exercise 1-3 days/week)',
    'Moderately Active (moderate exercise 3-5 days/week)',
    'Very Active (hard exercise 6-7 days/week)',
    'Extremely Active (very hard exercise, physical job)',
  ];

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  String? _validateConfirmPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please confirm your password';
    }
    if (value != _passwordController.text) {
      return 'Passwords do not match';
    }
    return null;
  }

  Future<void> _signUp() async {
    if (!_formKey.currentState!.validate()) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all required fields')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final authService = context.read<AuthService>();
      final dbService = context.read<DatabaseService>();

      // Step 1: Create auth account
      final result = await authService.signUp(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        firstName: _firstNameController.text.trim(),
        lastName: _lastNameController.text.trim(),
      );

      if (!result['success']) {
        setState(() => _isLoading = false);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result['message'])),
        );
        return;
      }

      final userId = result['userId'] as String;


      final profileSuccess = await dbService.createOrUpdateCompleteProfile(
        userId: userId,
        firstName: _firstNameController.text.trim(),
        lastName: _lastNameController.text.trim(),
        sex: _sex,
        age: _age,
        height: _height,
        ethnicity: _ethnicity,
        location: _locationController.text.trim().isEmpty 
            ? null 
            : _locationController.text.trim(),
        activityLevel: _activityLevel,
      );

      if (!profileSuccess) {
        setState(() => _isLoading = false);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to save profile information')),
        );
        return;
      }

      // Step 3: Add conditions - PASS userId EXPLICITLY
      if (_selectedConditions.isNotEmpty) {
        for (var condition in _selectedConditions) {
          await dbService.addCondition(condition, userId: userId);
        }
      }

      // Step 4: Add medications - PASS userId EXPLICITLY
      if (_selectedMedications.isNotEmpty) {
        for (var medication in _selectedMedications) {
          await dbService.addMedication(medication, userId: userId);
        }
      }

      // Step 5: Final verification - fetch profile using userId
      await dbService.fetchUserProfile(userId: userId);
      
      final finalProfile = dbService.userProfile;

      setState(() => _isLoading = false);

      if (!mounted) return;

      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Account created successfully!'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );

      // Navigate to home
      await Future.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;
      
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
      
    } catch (e) {
      setState(() => _isLoading = false);
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('An error occurred: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Account'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Account Information
                _buildSectionHeader('Account Information'),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _firstNameController,
                        decoration: const InputDecoration(
                          labelText: 'First Name',
                          hintText: 'John',
                        ),
                        validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: TextFormField(
                        controller: _lastNameController,
                        decoration: const InputDecoration(
                          labelText: 'Last Name',
                          hintText: 'Doe',
                        ),
                        validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _emailController,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    hintText: 'john.doe@example.com',
                  ),
                  keyboardType: TextInputType.emailAddress,
                  validator: (v) => (v?.isEmpty ?? true) || !v!.contains('@') 
                      ? 'Enter valid email' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    hintText: 'Min 6 characters',
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                  obscureText: _obscurePassword,
                  validator: (v) => (v?.isEmpty ?? true) || v!.length < 6 
                      ? 'Min 6 characters' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _confirmPasswordController,
                  decoration: InputDecoration(
                    labelText: 'Confirm Password',
                    hintText: 'Re-enter password',
                    suffixIcon: IconButton(
                      icon: Icon(_obscureConfirmPassword ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
                    ),
                  ),
                  obscureText: _obscureConfirmPassword,
                  validator: _validateConfirmPassword,
                ),
                
                const SizedBox(height: 32),
                
                // Personal Information
                _buildSectionHeader('Personal Information'),
                const SizedBox(height: 16),
                
                Text('Sex *', style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: ChoiceChip(
                        label: const Text('Male'),
                        selected: _sex == 'Male',
                        onSelected: (selected) {
                          if (selected) setState(() => _sex = 'Male');
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ChoiceChip(
                        label: const Text('Female'),
                        selected: _sex == 'Female',
                        onSelected: (selected) {
                          if (selected) setState(() => _sex = 'Female');
                        },
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                Text('Age: $_age *', style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                Slider(
                  value: _age.toDouble(),
                  min: 18,
                  max: 100,
                  divisions: 82,
                  label: _age.toString(),
                  onChanged: (value) => setState(() => _age = value.toInt()),
                ),
                
                const SizedBox(height: 16),
                Text(
                  _height != null ? 'Height: $_height cm *' : 'Height (cm) *',
                  style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    hintText: '170',
                    suffixText: 'cm',
                    border: OutlineInputBorder(),
                    helperText: 'Enter height in centimeters (50-250 cm)',
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Height is required';
                    }
                    final heightValue = int.tryParse(value);
                    if (heightValue == null) {
                      return 'Please enter a valid number';
                    }
                    if (heightValue < 50 || heightValue > 250) {
                      return 'Height must be between 50-250 cm';
                    }
                    return null;
                  },
                  onChanged: (value) {
                    final heightValue = int.tryParse(value);
                    setState(() => _height = heightValue);
                  },
                ),
                
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: _ethnicity,
                  decoration: const InputDecoration(
                    labelText: 'Ethnicity',
                    hintText: 'Select your ethnicity',
                  ),
                  items: _ethnicityOptions.map((ethnicity) {
                    return DropdownMenuItem(
                      value: ethnicity,
                      child: Text(ethnicity, style: TextStyle(fontSize: 14)),
                    );
                  }).toList(),
                  onChanged: (value) => setState(() => _ethnicity = value),
                ),
                
                const SizedBox(height: 16),
                TextFormField(
                  controller: _locationController,
                  decoration: const InputDecoration(
                    labelText: 'Location',
                    hintText: 'City, Country (e.g., Singapore, Singapore)',
                    helperText: 'Helps AI provide location-specific dietary suggestions',
                  ),
                  textCapitalization: TextCapitalization.words,
                ),
                
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: _activityLevel,
                  decoration: const InputDecoration(
                    labelText: 'Activity Level',
                    hintText: 'Select your activity level',
                  ),
                  items: _activityLevelOptions.map((level) {
                    return DropdownMenuItem(
                      value: level,
                      child: Text(
                        level.split(' (')[0],
                        style: TextStyle(fontSize: 14),
                      ),
                    );
                  }).toList(),
                  onChanged: (value) => setState(() => _activityLevel = value),
                ),
                
                const SizedBox(height: 32),
                
                // Health Information
                _buildSectionHeader('Health Information'),
                const SizedBox(height: 16),
                
                Text('Preexisting Conditions', 
                    style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    'Type 1 Diabetes',
                    'Type 2 Diabetes',
                    'Hypertension',
                    'High Cholesterol',
                    'Heart Disease',
                    'Kidney Disease',
                  ].map((condition) {
                    return FilterChip(
                      label: Text(condition, style: TextStyle(fontSize: 12)),
                      selected: _selectedConditions.contains(condition),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedConditions.add(condition);
                          } else {
                            _selectedConditions.remove(condition);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
                
                const SizedBox(height: 24),
                Text("Medications You're Taking", 
                    style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    'Metformin',
                    'Insulin',
                    'Glipizide',
                    'Jardiance',
                    'Ozempic',
                    'Lantus',
                  ].map((medication) {
                    return FilterChip(
                      label: Text(medication, style: TextStyle(fontSize: 12)),
                      selected: _selectedMedications.contains(medication),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedMedications.add(medication);
                          } else {
                            _selectedMedications.remove(medication);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
                
                const SizedBox(height: 32),
                
                // Create Account Button
                ElevatedButton(
                  onPressed: _isLoading ? null : _signUp,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.all(18),
                  ),
                  child: _isLoading
                      ? Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text('Creating account...'),
                          ],
                        )
                      : const Text('Create Account', style: TextStyle(fontSize: 16)),
                ),
                const SizedBox(height: 16),
                Text(
                  '* Required fields',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Color(0xFF6366F1),
          ),
        ),
        const SizedBox(height: 4),
        Container(
          height: 2,
          width: 40,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
            ),
          ),
        ),
      ],
    );
  }
}