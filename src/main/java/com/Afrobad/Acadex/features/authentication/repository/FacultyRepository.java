package com.Afrobad.Acadex.features.authentication.repository;

import com.Afrobad.Acadex.features.authentication.entity.Faculty;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface FacultyRepository
        extends JpaRepository<Faculty, Long> {

    Optional<Faculty> findByEmployeeId(String employeeId);

    Optional<Faculty> findByEmail(String email);

    Optional<Faculty> findByEmployeeIdAndEmail(
            String employeeId,
            String email
    );

    boolean existsByEmployeeId(String employeeId);

    boolean existsByEmail(String email);
}
