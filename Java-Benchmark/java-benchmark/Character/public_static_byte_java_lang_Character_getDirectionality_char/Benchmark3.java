

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Byte output_1 = Character.getDirectionality(input_1_0);
        Byte output_2 = Character.getDirectionality(input_2_0);

        
        // Compare output
        if (output_1 == 13 && output_2 == 7) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

