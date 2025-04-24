

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Boolean output_1 = Character.isJavaIdentifierPart(input_1_0);
        Boolean output_2 = Character.isJavaIdentifierPart(input_2_0);

        
        // Compare output
        if (output_1 == false && output_2 == true) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

