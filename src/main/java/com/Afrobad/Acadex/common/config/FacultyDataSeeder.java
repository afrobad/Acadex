package com.Afrobad.Acadex.common.config;

import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

import com.Afrobad.Acadex.features.authentication.entity.Faculty;
import com.Afrobad.Acadex.features.authentication.enums.Role;
import com.Afrobad.Acadex.features.authentication.repository.FacultyRepository;

import lombok.RequiredArgsConstructor;

@Configuration
@RequiredArgsConstructor
public class FacultyDataSeeder {

    private final FacultyRepository facultyRepository;

    private final PasswordEncoder passwordEncoder;

    @Bean
    public CommandLineRunner seedFacultyData() {

        return args -> {

            createFaculty(
                    "FAC-1001",
                    "Rahat Islam",
                    "rahat.swe@diu.edu.bd",
                    "Acadex@2026!",
                    Role.FACULTY
            );

            createFaculty(
                    "FAC-1002",
                    "Demo Faculty Two",
                    "demo2.swe@diu.edu.bd",
                    "Acadex@2026!",
                    Role.FACULTY
            );

            createFaculty(
                    "FAC-1003",
                    "Acadex Administrator",
                    "demo3.swe@diu.edu.bd",
                    "Acadex@2026!",
                    Role.ADMIN
            );

        };
    }

    private void createFaculty(
            String employeeId,
            String fullName,
            String email,
            String password,
            Role role
    ) {

        if (facultyRepository.existsByEmployeeId(employeeId)) {
            return;
        }

        if (facultyRepository.existsByEmail(email)) {
            return;
        }

        Faculty faculty = Faculty.builder()

                .employeeId(employeeId)

                .fullName(fullName)

                .email(email)

                .password(passwordEncoder.encode(password))

                .role(role)

                .enabled(true)

                .build();

        facultyRepository.save(faculty);

        System.out.println(
                "Faculty account created: " + employeeId
        );
    }
}
