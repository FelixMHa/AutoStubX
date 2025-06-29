package org.example;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import java.util.List;

@AllArgsConstructor
@NoArgsConstructor
@Getter
public class JavaFunctionExport {
    private String owner;
    private String name;
    private String genericString;
    private String returnType;
    private List<String> paramTypes;
}