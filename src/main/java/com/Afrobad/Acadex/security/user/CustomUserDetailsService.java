//Spring Security needs a way to retrieve faculty information from MySQL during authentication.

package com.Afrobad.Acadex.security.user;

import com.Afrobad.Acadex.features.authentication.entity.Faculty;
import com.Afrobad.Acadex.features.authentication.enums.Role;
import com.Afrobad.Acadex.features.authentication.repository.FacultyRepository;

import lombok.RequiredArgsConstructor;

import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final FacultyRepository facultyRepository;

    @Override
    public UserDetails loadUserByUsername(String employeeId)
            throws UsernameNotFoundException {

        Faculty faculty = facultyRepository
                .findByEmployeeId(employeeId)
                .orElseThrow(() ->
                    new UsernameNotFoundException(
                        "Faculty not found: " + employeeId
                    )
                );

        return User.builder()
                .username(faculty.getEmployeeId())
                .password(faculty.getPassword())
                .authorities("ROLE_" + ((Role) faculty.getRole()).name())
                .disabled(!faculty.getEnabled())
                .build();
    }
}
