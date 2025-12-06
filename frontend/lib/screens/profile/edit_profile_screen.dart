import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/database_service.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({Key? key}) : super(key: key);

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _locationController = TextEditingController();
  
  String _sex = 'Male';
  String? _ethnicity;
  int _age = 50;
  int? _height;
  String? _activityLevel;
  final _heightController = TextEditingController();
  
  List<String> _selectedConditions = [];
  List<String> _selectedMedications = [];
  
  bool _isLoading = false;
  bool _dataLoaded = false;

  final List<String> _ethnicityOptions = [
    'Chinese',
    'Indian',
    'Malay',
    'Eurasian',
    'Other Asian',
    'Black or African American',
    'Hispanic or Latino',
    'White or Caucasian',
    'Native American or Alaska Native',
    'Native Hawaiian or Pacific Islander',
    'Middle Eastern or North African',
    'Mixed or Multiracial',
    'Other',
  ];

  final List<String> _activityLevelOptions = [
    'Sedentary (little or no exercise)',
    'Lightly Active (light exercise 1-3 days/week)',
    'Moderately Active (moderate exercise 3-5 days/week)',
    'Very Active (hard exercise 6-7 days/week)',
    'Extremely Active (very hard exercise, physical job)',
  ];

  @override
  void initState() {
    super.initState();
    _loadUserData();
  }

  Future<void> _loadUserData() async {
    final dbService = context.read<DatabaseService>();
    final profile = dbService.userProfile;
    
    if (profile != null) {
      setState(() {
        _firstNameController.text = profile.firstName ?? '';
        _lastNameController.text = profile.lastName ?? '';
        _locationController.text = profile.location ?? '';
        _sex = profile.sex ?? 'Male';
        _ethnicity = profile.ethnicity;
        _age = profile.age ?? 50;
        _height = profile.height;
        _heightController.text = profile.height?.toString() ?? '';
        _activityLevel = profile.activityLevel;
      });
    }
    
    // Load conditions and medications
    final conditions = await dbService.getConditions();
    final medications = await dbService.getMedications();
    
    setState(() {
      _selectedConditions = conditions;
      _selectedMedications = medications;
      _dataLoaded = true;
    });
  }

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _locationController.dispose();
    _heightController.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final dbService = context.read<DatabaseService>();
    final currentProfile = dbService.userProfile;
    if (currentProfile == null) return;

    // Update profile
    final heightValue = _heightController.text.trim().isEmpty 
        ? null 
        : int.tryParse(_heightController.text.trim());
    
    final updatedProfile = currentProfile.copyWith(
      firstName: _firstNameController.text.trim(),
      lastName: _lastNameController.text.trim(),
      location: _locationController.text.trim().isEmpty 
          ? null 
          : _locationController.text.trim(),
      ethnicity: _ethnicity,
      sex: _sex,
      age: _age,
      height: heightValue,
      activityLevel: _activityLevel,
    );

    final success = await dbService.updateUserProfile(updatedProfile);

    setState(() => _isLoading = false);

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated successfully')),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to update profile')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_dataLoaded) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Edit Details'),
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
          elevation: 0,
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Details'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Name Section
              _buildSectionHeader('Name'),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _firstNameController,
                      decoration: const InputDecoration(
                        labelText: 'First Name',
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
                      ),
                      validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 32),
              
              // Personal Information Section
              _buildSectionHeader('Personal Information'),
              const SizedBox(height: 16),
              
              Text('Sex', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
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
              
              const SizedBox(height: 24),
              Text('Age: $_age', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
              Slider(
                value: _age.toDouble(),
                min: 18,
                max: 100,
                divisions: 82,
                label: _age.toString(),
                onChanged: (value) => setState(() => _age = value.toInt()),
              ),
              
              const SizedBox(height: 16),
              Text('Height (cm)', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
              const SizedBox(height: 8),
              TextField(
                controller: _heightController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  hintText: '170',
                  suffixText: 'cm',
                  helperText: 'Height in centimeters',
                ),
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
                  helperText: 'Helps AI provide culturally relevant suggestions',
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
                  hintText: 'City, Country',
                  helperText: 'Helps AI provide location-specific dietary suggestions',
                  prefixIcon: Icon(Icons.location_on),
                ),
                textCapitalization: TextCapitalization.words,
              ),
              
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _activityLevel,
                decoration: const InputDecoration(
                  labelText: 'Activity Level',
                  hintText: 'Select your activity level',
                  helperText: 'Helps AI calculate your caloric needs',
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
              
              // Health Information Section
              _buildSectionHeader('Health Information'),
              const SizedBox(height: 16),
              
              Text('Preexisting Conditions', 
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.blue[200]!),
                ),
                child: _selectedConditions.isEmpty
                    ? Text('No conditions added', 
                        style: TextStyle(color: Colors.grey[600], fontSize: 14))
                    : Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _selectedConditions.map((condition) {
                          return Chip(
                            label: Text(condition, style: TextStyle(fontSize: 12)),
                            backgroundColor: Colors.blue[100],
                            deleteIcon: Icon(Icons.info_outline, size: 16),
                            onDeleted: null,
                          );
                        }).toList(),
                      ),
              ),
              const SizedBox(height: 8),
              Text(
                'To add or remove conditions, please contact support',
                style: TextStyle(fontSize: 12, color: Colors.grey[600], fontStyle: FontStyle.italic),
              ),
              
              const SizedBox(height: 24),
              Text('Medications', 
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.green[50],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green[200]!),
                ),
                child: _selectedMedications.isEmpty
                    ? Text('No medications added', 
                        style: TextStyle(color: Colors.grey[600], fontSize: 14))
                    : Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _selectedMedications.map((medication) {
                          return Chip(
                            label: Text(medication, style: TextStyle(fontSize: 12)),
                            backgroundColor: Colors.green[100],
                            deleteIcon: Icon(Icons.info_outline, size: 16),
                            onDeleted: null,
                          );
                        }).toList(),
                      ),
              ),
              const SizedBox(height: 8),
              Text(
                'To add or remove medications, please contact support',
                style: TextStyle(fontSize: 12, color: Colors.grey[600], fontStyle: FontStyle.italic),
              ),
              
              const SizedBox(height: 32),
              
              // Info Box
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.purple[50],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.purple[200]!),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.purple[700], size: 24),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Your information helps our AI provide personalized health suggestions based on your location, activity level, and background.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.purple[900],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Save Button
              ElevatedButton(
                onPressed: _isLoading ? null : _saveProfile,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(18),
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Text('Save Details', style: TextStyle(fontSize: 16)),
              ),
            ],
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